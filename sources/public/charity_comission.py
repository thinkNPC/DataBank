import io
import json
import logging
import zipfile
from functools import partial

import numpy as np
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

CC_ACTIVE = DataAsset(
    name="Estimated active charities",
    inputs={"cc": CC_MAIN},
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
    cc = data["CC"]
    area = data["CC_Area"]
    lkp = data["ltla_utla"]

    # merge so that only active charities are kept
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
        lkp[["utla_code", "utla_name", "utla_clean"]],
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

    return df.drop(
        columns=["split", "utla_clean", "utla_name_cc", "geographic_area_type"]
    )


CC_AREA_ACTIVE = DataAsset(
    name="Active charities by area",
    inputs={"CC": CC_ACTIVE, "CC_Area": CC_AREA, "ltla_utla": LTLA_UTLA},
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
    inputs={"cc": CC_AREA_ACTIVE},
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
        df, "UTLA", "count_per_1000", zmax=get_n_highest(df, "count_per_1000", 3)
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
        yaxis=dict(title="Spent per head (??)"),
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
