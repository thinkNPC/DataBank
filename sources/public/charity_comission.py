import io
import json
import logging
import zipfile
from functools import partial

import numpy as np
import pandas as pd
import requests
import seaborn as sns

from models import DataAsset, DataDate, DataSource, DateMeta, Organisations, SourceType
from plotting import hex, style
from sources.public.census import POP_LA
from sources.public.geoportal import LTLA_UTLA
from sources.public.levellingup import LVL_BY_UTLA
from utils import CACHE, DATA_DIR

CC_ENDPOINT = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity.zip"
CC_COLS = [
    "date_of_extract",
    "organisation_number",
    "registered_charity_number",
    "linked_charity_number",
    "charity_name",
    "charity_type",
    "charity_registration_status",
    "date_of_registration",
    "date_of_removal",
    "charity_reporting_status",
    "latest_acc_fin_period_start_date",
    "latest_acc_fin_period_end_date",
    "latest_income",
    "latest_expenditure",
    "charity_contact_address1",
    "charity_contact_address2",
    "charity_contact_address3",
    "charity_contact_address4",
    "charity_contact_address5",
    "charity_contact_postcode",
    "charity_contact_phone",
    "charity_contact_email",
    "charity_contact_web",
    "charity_company_registration_number",
    "charity_insolvent",
    "charity_in_administration",
    "charity_previously_excepted",
    "charity_is_cdf_or_cif",
    "charity_is_cio",
    "cio_is_dissolved",
    "date_cio_dissolution_notice",
    "charity_activities",
    "charity_gift_aid",
    "charity_has_land",
]

CC_AREA_EP = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_area_of_operation.zip"
CC_CATEGORY_EP = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_classification.zip"
CC_HISTORY_EP = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_annual_return_history.zip"


APPROX_MONTH = pd.Timedelta("31 days")


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


@CACHE.memoize()
def get_cc_main():
    datadate = get_charity_commission_dataset(CC_ENDPOINT, "publicextract.charity.json")
    datadate.df = datadate.df[
        [
            "organisation_number",
            "registered_charity_number",
            "linked_charity_number",
            "charity_name",
            "charity_type",
            "charity_registration_status",
            "charity_reporting_status",
            "latest_income",
            "latest_expenditure",
            "charity_insolvent",
            "charity_in_administration",
        ]
    ]
    return datadate


@CACHE.memoize()
def get_cc_area():
    datadate = get_charity_commission_dataset(
        CC_AREA_EP, "publicextract.charity_area_of_operation.json"
    )
    datadate.df = datadate.df[
        [
            "organisation_number",
            "registered_charity_number",
            "linked_charity_number",
            "geographic_area_type",
            "geographic_area_description",
        ]
    ]
    return datadate


@CACHE.memoize()
def get_cc_category():
    datadate = get_charity_commission_dataset(
        CC_CATEGORY_EP, "publicextract.charity_classification.json"
    )
    return datadate


def get_cc_history():
    datadate = get_charity_commission_dataset(
        CC_HISTORY_EP, "publicextract.charity_annual_return_history.json"
    )
    datadate.df = datadate.df[
        [
            "date_of_extract",
            "organisation_number",
            "ar_cycle_reference",
            "total_gross_income",
            "total_gross_expenditure",
        ]
    ]
    df = datadate.df
    return datadate


@CACHE.memoize()
def get_grantmaking():
    datadate = get_charity_commission_dataset(
        "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_annual_return_parta.zip",
        "publicextract.charity_annual_return_parta.json",
    )
    df = datadate.df
    grantmakers = df[df["grant_making_is_main_activity"] == True]
    grantmakers = df[["organisation_number"]].drop_duplicates()
    datadate.df = grantmakers
    return datadate


@CACHE.memoize()
def filter_active_charities(data):
    df = data["cc"]

    # date_of_registration, ~30000 in last five years
    # acc fin period - not needed as report status covers this
    # ~10% of active charities have income/expenditure of 0
    # 99% have address and phone
    # 85% have email, 66% have website
    # Uniform spread between 0-80 descriptions

    print("no filter N =", len(df))
    # 'registered' or 'removed'
    df = df[df["charity_registration_status"] == "Registered"]
    # ~70% of registered charities have submission recieved, others are overdue or sim
    df = df[df["charity_reporting_status"] == "Submission Received"]

    df = df[df["charity_insolvent"] == False]
    df = df[df["charity_in_administration"] == False]
    print("after filter N =", len(df))

    if False:
        import matplotlib.pyplot as plt

        col = "charity_activities"
        fig = df[col].hist(log=True, alpha=0.5, bins=20)
        plt.savefig("temp-post.png")

    df = df[
        [
            "organisation_number",
            "registered_charity_number",
            "linked_charity_number",
            "charity_name",
            "latest_income",
            "latest_expenditure",
        ]
    ]
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

CC_CATEGORY = DataSource(
    name="Charity categories",
    data_getter=get_cc_category,
    org=Organisations.charity_commission,
    source_type=SourceType.webscrape,
    url="https://register-of-charities.charitycommission.gov.uk/register/full-register-download",
    dateMeta=DateMeta(update_freq=APPROX_MONTH),
    description="""
    """,
)

CC_HISTORY = DataSource(
    name="Charity annual return history",
    data_getter=get_cc_history,
    org=Organisations.charity_commission,
    source_type=SourceType.webscrape,
    url="https://register-of-charities.charitycommission.gov.uk/register/full-register-download",
    dateMeta=DateMeta(update_freq=APPROX_MONTH),
    description="""
    """,
)

CC_GRANTMAKER = DataSource(
    name="Charity org number grantmaking flag",
    data_getter=get_grantmaking,
    org=Organisations.charity_commission,
    source_type=SourceType.webscrape,
    url="https://register-of-charities.charitycommission.gov.uk/register/full-register-download",
    dateMeta=DateMeta(update_freq=APPROX_MONTH),
    description="""
    """,
)


def remove_grantmakers(df):
    print("removing grant makers")
    return df[
        df["organisation_number"].isin(CC_GRANTMAKER.get_data()["organisation_number"])
    ]


CC_ACTIVE = DataAsset(
    name="Estimated active charities",
    inputs={"cc": CC_MAIN, "cc_cat": CC_CATEGORY},
    processer=filter_active_charities,
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
    cc = data["CC"]
    area = data["CC_Area"]
    lkp = data["ltla_utla"]

    # merge so that only active charities are kept
    cc = remove_grantmakers(cc)
    drop_cols = ["linked_charity_number"]
    org_id_cols = ["organisation_number", "registered_charity_number"]
    split_cols = ["latest_expenditure", "latest_income"]
    df = area.drop(columns=drop_cols,).merge(
        cc[org_id_cols + split_cols],
        on=["organisation_number", "registered_charity_number"],
        how="inner",
    )

    # only interested in charities with a LA documented
    df = df[df["geographic_area_type"] == "Local Authority"]
    df = df.rename(
        columns={
            "geographic_area_description": "utla_name",
        }
    )

    # split expenditure over las mentioned per charity
    split_las = df["organisation_number"].value_counts()
    split_las = pd.DataFrame(split_las).reset_index()
    split_las = split_las.rename(
        columns={
            "index": "organisation_number",
            "organisation_number": "split",
        }
    )
    df = df.merge(split_las, how="left")

    df[split_cols] = df[split_cols].divide(df["split"], axis=0)

    # Charity commission do not use standard area codes, so clean them up
    df["utla_clean"] = df["utla_name"].apply(clean_utla_names)
    lkp["utla_clean"] = lkp["utla_name"].apply(clean_utla_names)
    df = df.merge(
        lkp[["utla_code", "utla_name", "utla_clean"]].drop_duplicates(),
        on="utla_clean",
        how="outer",
        suffixes=("_cc", "_ons"),
    )

    # fill unmatched ons utla names with CC names, they don't have utla_codes
    df = df.rename(columns={"utla_name_ons": "utla_name"})
    df["utla_name"] = df["utla_name"].fillna(df["utla_name_cc"])
    no_match = df["utla_code"].isnull()
    logging.warning(
        f"No matches for {[name for name in df.loc[no_match, 'utla_name_cc'].unique()]}"
    )

    return df.drop(columns=["utla_clean", "utla_name_cc", "geographic_area_type"])


CC_BY_AREA = DataAsset(
    name="Charities by area",
    inputs={"CC": CC_MAIN, "CC_Area": CC_AREA, "ltla_utla": LTLA_UTLA},
    processer=charities_by_la,
    description=("Where charity has UTLA or region info."),
)


def n_charities_by_la(data):
    df = data["cc"]
    df = df[["utla_code", "utla_name", "organisation_number", "latest_expenditure"]]
    df = (
        df.groupby(["utla_code", "utla_name"])
        .agg({"organisation_number": "count", "latest_expenditure": "sum"})
        .rename(
            columns={
                "organisation_number": "count",
                "latest_expenditure": "total_spent",
            }
        )
        .sort_values("total_spent", ascending=False)
        .reset_index()
    )

    df = df[["utla_code", "utla_name", "count", "total_spent"]]
    codes_not_in_set = data["cc"].loc[
        data["cc"]["organisation_number"].isnull(), "utla_code"
    ]
    df.loc[df["utla_code"].isin(codes_not_in_set), ["count", "total_spent"]] = np.nan

    return df


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
    inputs={"cc": CC_BY_AREA},
    processer=n_charities_by_la,
    description=("Only ~60\% of charities have a UTLA defined to them."),
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
    return df.sort_values(col, ascending=False).iloc[n][col]


def charity_map(data):
    df = data["n_charities"]

    fig = hex.plot_hexes(
        df, "UTLA", "count_per_1000", zmax=get_n_highest(df, "count_per_1000", 3),
    )
    return fig


def charity_spent_map(data):
    df = data["n_charities"]
    fig = hex.plot_hexes(
        df, "UTLA", "spent_per_head", zmax=get_n_highest(df, "spent_per_head", 3)
    )
    return fig


def charity_spend_by_lvlup_strip(data):
    df = pd.merge(
        data["n_charities"],
        data["lvlup_areas"].drop(columns="utla_name"),
        how="outer",
        on="utla_code",
    )
    import plotly.express as px

    pal = sns.color_palette("magma_r").as_hex()
    pal = [pal[1], pal[3], pal[5]]
    df = df.sort_values("Category").dropna(subset=["Category", "spent_per_head"])
    df["Category"] = df["Category"].round(0).astype(int)
    df["spent_per_head"] = df["spent_per_head"].round(0).astype(int)
    cat = df.groupby("Category").median()
    print(cat)
    fig = px.strip(
        df,
        x="Category",
        y="spent_per_head",
        color="Category",
        hover_data=["utla_name"],
        log_y=True,
        color_discrete_sequence=pal,
    )
    fig.update_layout(
        xaxis=dict(title="Levelling up priority"),
        yaxis=dict(title="Spent per head (£)"),
        showlegend=False,
    )
    style.npc_style(fig, logo_pos="left")

    return fig


def charity_spend_by_lvlup_hex(data):
    df = pd.merge(
        data["n_charities"],
        data["lvlup_areas"].drop(columns="utla_name"),
        how="outer",
        on="utla_code",
    )
    df["category_rounded"] = df["Category"].round()
    m = df.groupby("category_rounded").mean()
    m = m[["count", "count_per_1000", "spent_per_head"]]
    m.to_csv("charity_per_head_and_spend_averages.csv")
    df.to_csv("charity_per_head_and_spend_lvl_up_area.csv")

    lvl1 = df.loc[df["Category"] == 1, "utla_code"]
    fig = hex.plot_hexes(
        df,
        "UTLA",
        "spent_per_head",
        zmax=get_n_highest(df, "spent_per_head", 3),
        highlight=lvl1,
    )

    df["Category"] = df["Category"].round(0)

    style.npc_style(fig)

    return fig


CharityDensityHex = DataAsset(
    name="Charities per 1000 people in each local authority hexmap",
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

CharitySpendLvlupStrip = DataAsset(
    name="Charities spend by levelling up area violin plot",
    inputs={
        "n_charities": NCharitiesUTLAPerHead,
        "lvlup_areas": LVL_BY_UTLA,
    },
    processer=charity_spend_by_lvlup_strip,
)

CharitySpendLvlupHex = DataAsset(
    name="Charities spend by levelling up area hexmap",
    inputs={
        "n_charities": NCharitiesUTLAPerHead,
        "lvlup_areas": LVL_BY_UTLA,
    },
    processer=charity_spend_by_lvlup_hex,
)


def combine_cc_history(data):
    area = data["cc_area"]
    df = data["cc_history"]

    # area = area[['organisation_number', 'split', 'utla_name']]
    df = df[["organisation_number", "ar_cycle_reference", "total_gross_expenditure"]]
    df = df.merge(area).sort_values(["split", "organisation_number"])
    df["total_gross_expenditure"] = df["total_gross_expenditure"].divide(
        df["split"], axis=0
    )
    df["year"] = 2000 + pd.to_numeric(df["ar_cycle_reference"].str[2:])
    df = df.drop(
        columns=["split", "latest_expenditure", "latest_income", "ar_cycle_reference"]
    )

    return df


CC_HISTORY_AREA = DataAsset(
    name="combine account history and area",
    inputs={"cc_history": CC_HISTORY, "cc_area": CC_BY_AREA},
    processer=combine_cc_history,
)


def level_up_spend_history(data):
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
    lvlup = data["lvlup_areas"]
    lvlup["Category"] = lvlup["Category"].round()
    lvlup_pops = utla_pop.merge(lvlup).groupby("Category").sum()
    df = (
        data["cc"][["utla_code", "year", "total_gross_expenditure"]]
        .groupby(["utla_code", "year"])
        .sum()
        .reset_index()
    )
    df = df.merge(data["lvlup_areas"])
    df["Category"] = df["Category"].round()
    df = df.groupby(["Category", "year"]).sum().reset_index()
    df = df.pivot(index="year", columns="Category", values="total_gross_expenditure")
    for col in df.columns:
        df[col] = df[col] / lvlup_pops.loc[col, "population"]
    return df


LVL_UP_AREA_HISTORY = DataAsset(
    name="Expenditure by levelling up area over time",
    inputs={
        "cc": CC_HISTORY_AREA,
        "lvlup_areas": LVL_BY_UTLA,
        "ltla_pop": POP_LA,
        "ltla_utla": LTLA_UTLA,
    },
    processer=level_up_spend_history,
)


def level_up_spend_history_chart(data):
    import plotly.express as px
    import plotly.graph_objects as go
    pal = sns.color_palette("magma_r").as_hex()
    pal = [pal[5], pal[3], pal[1]]

    df = data['df']
    cols = df.columns
    df = df.reset_index()

    df = df[df["year"] >= 2018]
    df = df[df["year"] <= 2021]

    labels = [
        '1 (places in most<br>need of investment)',
        '2',
        '3'
    ]
    fig = go.Figure()
    for i, col in enumerate(cols):
        fig.add_trace(
            go.Line(
                x=df['year'],
                y=df[col],
                marker=dict(
                    color=pal[i],
                ),
                name=col,
                #name=labels[i],
            )
        )

    fig.update_layout(
        xaxis=dict(title=""),
        yaxis=dict(
            title="Charity spend per head",
            range=[0, df[cols].max().max() * 1.05],
            tickprefix='£'
        ),
        legend=dict(
            traceorder='reversed',
            title='Levelling up priority'
        )
    )

    ay = [20, -20, 20]
    labels = [
        'Priority area 1<br>highest need',
        'Priority area 2',
        'Priority area 3'
    ]
    # for i, col in enumerate([1,2,3]):
    #     fig.add_annotation(
    #         x=2018,
    #         y=df.set_index('year').loc[2018, col],
    #         text=labels[i],
    #         font=dict(color=pal[i]),
    #         ay=ay[i],
    #         align='left'
    #     )
    fig.add_annotation(
        x=2019,
        y=df.set_index('year').loc[2019, cols[0]],
        text='Levelling up fund<br>announced in 2019',
        showarrow=False,    #
        yshift=-30,
    )
    fig.add_annotation(
        x=2021,
        y=df.set_index('year').loc[2021, cols[0]],
        text='Funding gap to priority<br>levelling up areas<br>has widened, not closed.',
        showarrow=False,
        yshift=-30,
        xshift=-30,
    )

    style.npc_style(fig, logo_pos="bottom")

    return fig


LVL_UP_AREA_HISTORY_CHART = DataAsset(
    name="Chart of expenditure by levelling up area over time",
    inputs={"df": LVL_UP_AREA_HISTORY},
    processer=level_up_spend_history_chart,
)


def focus_area_data(data):
    pop = data["ltla_pop"]
    lkp = data["ltla_utla"]
    utla_pop = (
        pd.merge(pop, lkp[["la_code", "utla_code", "utla_name"]], on="la_code")
        .groupby(
            ["utla_code", "utla_name"],
        )
        .sum(numeric_only=True)
        .reset_index()
        .set_index('utla_name')
    )
    lvlup = data["lvlup_areas"]
    lvlup["Category"] = lvlup["Category"].round()
    utla_pop = utla_pop.merge(lvlup)
    df = (
        data["cc"][["utla_name", "year", "total_gross_expenditure"]]
        .groupby(["utla_name", "year"])
        .sum()
        .reset_index()
    )

    areas = ['Nottingham', 'Kent', 'Rochdale']
    df = df[df['utla_name'].isin(areas)]
    df = df.merge(utla_pop.reset_index(), how='left')
    df['spend'] = df['total_gross_expenditure'] / df['population']
    df = df.pivot(index='year', columns='utla_name', values='spend')
    return df


CC_3_AREAS = DataAsset(
    name="3 focus areas data",
    inputs={
        "cc": CC_HISTORY_AREA,
        "lvlup_areas": LVL_BY_UTLA,
        "ltla_pop": POP_LA,
        "ltla_utla": LTLA_UTLA,
    },
    processer=focus_area_data,
)

CC_3_AREAS_CHART = DataAsset(
    name="Chart of expenditure by focus area over time",
    inputs={"df": CC_3_AREAS},
    processer=level_up_spend_history_chart,
)

def area_spend_data(data):
    pop = data["ltla_pop"]
    lkp = data["ltla_utla"]
    utla_pop = (
        pd.merge(pop, lkp[["la_code", "utla_code", "utla_name"]], on="la_code")
        .groupby(
            ["utla_code", "utla_name"],
        )
        .sum(numeric_only=True)
        .reset_index()
        .set_index('utla_name')
    )
    lvlup = data["lvlup_areas"]
    lvlup["Category"] = lvlup["Category"].round()
    utla_pop = utla_pop.merge(lvlup)
    df = (
        data["cc"][["utla_name", "year", "total_gross_expenditure"]]
        .groupby(["utla_name", "year"])
        .sum()
        .reset_index()
    )
    df = df.merge(utla_pop.reset_index(), how='left')
    df['spend'] = df['total_gross_expenditure'] / df['population']

    df = df.pivot(index='year', columns='utla_name', values='spend')
    return df


CC_SPEND_YEAR_UTLA = DataAsset(
    name="Area spend by year table",
    inputs={
        "cc": CC_HISTORY_AREA,
        "lvlup_areas": LVL_BY_UTLA,
        "ltla_pop": POP_LA,
        "ltla_utla": LTLA_UTLA,
    },
    processer=area_spend_data,
)