import io
import json
import logging
import zipfile
from functools import partial

import pandas as pd
import requests
import seaborn as sns

from models import (DataAsset, DataDate, DataSource, DateMeta, Organisations,
                    SourceType)
from plotting import hex, style
from sources.public.census import POP_LA
from sources.public.geoportal import LTLA_UTLA
from sources.public.levellingup import LVL_BY_UTLA
from utils import CACHE, DATA_DIR

CC_ENDPOINT = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity.zip"
CC_AREA_EP = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_area_of_operation.zip"

APPROX_MONTH = pd.Timedelta("31 days")


@CACHE.memoize()
def get_charity_commission_dataset(endpoint, fname):
    r = requests.get(endpoint)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert fname in z.namelist(), z.namelist()
        with z.open(fname) as f:
            data = json.load(f)
    date = data[0]["date_of_extract"]
    assert all([date == entry["date_of_extract"] for entry in data])

    df = pd.DataFrame.from_dict(data)
    date = pd.to_datetime(date)
    return DataDate(df, DateMeta(publish_date=date))

def get_cc_main():
    datadate = get_charity_commission_dataset(
        CC_ENDPOINT, 'publicextract.charity.json'
    )
    return datadate

def get_cc_area():
    datadate = get_charity_commission_dataset(
        CC_AREA_EP, "publicextract.charity_area_of_operation.json"
    )
    return datadate


def filter_active_charities(data):
    df = data['cc']

    # date_of_registration, ~30000 in last five years
    # acc fin period - not needed as report status covers this
    # ~10% of active charities have income/expenditure of 0
    # 99% have address and phone
    # 85% have email, 66% have website
    # Uniform spread between 0-80 descriptions

    print('no filter N =', len(df))
    # 'registered' or 'removed'
    df = df[df['charity_registration_status'] == 'Registered']
    # ~70% of registered charities have submission recieved, others are overdue or sim
    df = df[df['charity_reporting_status'] == 'Submission Received']
    
    df = df[df['charity_insolvent'] == False]
    df = df[df['charity_in_administration'] == False]
    print('after filter N =', len(df))

    if False:
        import matplotlib.pyplot as plt
        col = 'charity_activities'
        fig = df[col].hist(log=True, alpha=0.5, bins=20)
        plt.savefig('temp-post.png')
    return df

CC_MAIN = DataSource(
    name="Charity comission summary table",
    data_getter=get_cc_main,
    org=Organisations.charity_commission,
    source_type=SourceType.webscrape,
    url="https://register-of-charities.charitycommission.gov.uk/register/full-register-download",
    dateMeta=DateMeta(update_freq=APPROX_MONTH),
    description="""
    Summary info of charities registered in England & Wales
    """,
)

CC_ACTIVE = DataAsset(
    name="Estimated active charities",
    inputs={'cc': CC_MAIN},
    processer=filter_active_charities,
)

CC_AREA = DataSource(
    name="Charity area of operation",
    data_getter=get_cc_area,
    org=Organisations.charity_commission,
    source_type=SourceType.webscrape,
    url="https://register-of-charities.charitycommission.gov.uk/register/full-register-download",
    dateMeta=DateMeta(update_freq=APPROX_MONTH),
    description="""
    Each row describes a charity and a geography.
    Charities often record multiple levels or geography,
    or multiple areas at the same level.
    """,
)



def clean_utla_names(s):
    return (
        s.lower()
        .removesuffix("city")
        .removeprefix("city of")
        .removesuffix(", city of")
        .removeprefix("county")
        .removesuffix(", county of")
        .replace("&", "and")
        .replace("st.", "st")
        .replace("rhondda cynon taff", "rhondda cynon taf")
        .strip()
    )


def charities_by_la(data):
    cc = data['CC']
    area = data["CC_Area"]
    lkp = data["ltla_utla"]

    
    # merge so that only active charities are kept
    drop_cols = ['date_of_extract', 'linked_charity_number']
    df = area.drop(
        columns=drop_cols,
    ).merge(
        cc, 
        on=['organisation_number', 'registered_charity_number'],
        how='inner',
    )

    # only interested in charities with a LA documented
    df = df[df["geographic_area_type"] == "Local Authority"]
    df = df.rename(
        columns={
            "geographic_area_description": "utla_name",
        }
    )

    # split expenditure over las mentioned per charity
    df = df[['organisation_number', 'latest_expenditure',
       'utla_name']]
    split_las = df['organisation_number'].value_counts()
    split_las = pd.DataFrame(split_las).reset_index()
    split_las = split_las.rename(columns={
        'index': 'organisation_number',
        'organisation_number': 'split',
    })
    df = df.merge(split_las, how='left')
    df['split_expenditure'] = df['latest_expenditure'].divide(df['split'])

    # aggregate to utla
    df = df[['utla_name', 'organisation_number', 'split_expenditure']]
    df = (
        df.groupby("utla_name")
        .agg({
            'organisation_number': 'count',
            'split_expenditure': 'sum'
        })
        .rename(columns={
            'organisation_number': 'count',
            'split_expenditure': 'total_spent',
        })
        .sort_values("total_spent", ascending=False)
        .reset_index()
    )


    # Charity commission do not use standard area codes, so clean them up
    df["utla_clean"] = df["utla_name"].apply(clean_utla_names)
    lkp["utla_clean"] = lkp["utla_name"].apply(clean_utla_names)
    df = df.merge(
        lkp, on="utla_clean", how='outer', suffixes=("_cc", "_ons")
    )

    # fill unmatched ons utla names with CC names, they don't have utla_codes
    df = df.rename(columns={"utla_name_ons": "utla_name"})
    df["utla_name"] = df["utla_name"].fillna(df["utla_name_cc"])
    print('ltla matched:', len(df))
    no_match = df["utla_code"].isnull()
    logging.warning(
        f"No matches for {[name for name in df.loc[no_match, 'utla_name_cc']]}"
    )
    df = df.drop_duplicates(subset=['utla_code'])

    return df[['utla_code', 'utla_name', 'count', 'total_spent']]


def normalise_charities_utla(data):
    pop = data["ltla_pop"]
    lkp = data["ltla_utla"]
    utla_pop = (
        pd.merge(pop, lkp[["la_code", "utla_code", "utla_name"]], on="la_code")
        .groupby(
            ["utla_code", "utla_name"],
        )
        .sum(numeric_only=True)
        .reset_index()
    )

    df = pd.merge(
        data["n_charities"],
        utla_pop,
        how="left",
    )
    df["count_per_1000"] = 1000 * df["count"] / df["population"]
    df["spent_per_head"] = df["total_spent"] / df["population"]

    df = df.sort_values("spent_per_head", ascending=False)
    return df
    

N_CHARITIES_UTLA = DataAsset(
    name="Number of active charities operational by UTLA",
    inputs={"CC": CC_ACTIVE, "CC_Area": CC_AREA, "ltla_utla": LTLA_UTLA},
    processer=charities_by_la,
    description=(
        "Only ~60\% of charities have a UTLA defined to them."
    )
)

NCharitiesUTLAPerHead = DataAsset(
    name="Number of charities operational by UTLA per head",
    inputs={
        "n_charities": N_CHARITIES_UTLA,
        "ltla_utla": LTLA_UTLA,
        "ltla_pop": POP_LA,
    },
    processer=normalise_charities_utla,
)

def get_n_highest(df, col, n):
    return (
        df
        .sort_values(col, ascending=False)
        .iloc[n][col]
    )

def charity_map(data):
    df = data["n_charities"]

    fig = hex.plot_hexes(df, "UTLA", "count_per_1000", 
                         zmax=get_n_highest(df, 'count_per_1000', 3))
    return fig


def charity_spent_map(data):
    df = data["n_charities"]
    print(df.sort_values('spent_per_head', ascending=False))
    fig = hex.plot_hexes(df, "UTLA", "spent_per_head", zmax=get_n_highest(df, 'spent_per_head', 3))
    return fig


def charity_lvlup_map(data):
    print(data)
    df = pd.merge(
        data['n_charities'],
        data['lvlup_areas'].drop(columns='utla_name'),
        how='outer',
        on='utla_code',
    )
    print(df)
    import plotly.express as px
    pal =sns.color_palette('magma_r').as_hex()
    pal = [pal[1], pal[3], pal[5]]
    df['Category'] = df['Category'].round(0)
    print(df.groupby('Category').count())
    print(df.groupby('Category').sum())
    print(df.sort_values('population', ascending=False))

    fig = px.strip(df, x='Category', y='spent_per_head', 
                   color='Category',
                   hover_data=['utla_name'],
                   log_y=True,
                   color_discrete_sequence=pal)
    style.npc_style(fig)
    
    return fig

CharityDensityHex = DataAsset(
    name="Charities per head in each local authority hexmap",
    inputs={
        "n_charities": NCharitiesUTLAPerHead,
    },
    processer=charity_map,
)

CharitySpendDensityHex = DataAsset(
    name="Charity expenditure per head in each local authority hexmap",
    inputs={
        "n_charities": NCharitiesUTLAPerHead,
    },
    processer=charity_spent_map,
)

CharityDesnityLvlup = DataAsset(
    name="Charities per head and levelling up areas",
    inputs={
        "n_charities": NCharitiesUTLAPerHead,
        'lvlup_areas': LVL_BY_UTLA,
    },
    processer=charity_lvlup_map,
)
