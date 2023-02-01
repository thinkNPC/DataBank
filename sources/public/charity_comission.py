import io
import json
import logging
import zipfile
from functools import partial

import pandas as pd
import requests

from models import (DataAsset, DataDate, DataSource, DateMeta, Organisations,
                    SourceType)
from sources.public.census import POP_LA
from sources.public.geoportal import LTLA_UTLA
from utils import CACHE, DATA_DIR

CC_ENDPOINT = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity.zip"
CC_AREA_EP = "https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_area_of_operation.zip"

APPROX_MONTH = pd.Timedelta("31 days")


@CACHE.memoize()
def get_charity_commission_dataset(endpoint, fname):
    r = requests.get(endpoint)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(fname) as f:
            data = json.load(f)
    date = data[0]["date_of_extract"]
    assert all([date == entry["date_of_extract"] for entry in data])

    df = pd.DataFrame.from_dict(data)
    date = pd.to_datetime(date)
    return DataDate(df, DateMeta(publish_date=date))


def get_cc_area():
    return get_charity_commission_dataset(
        CC_AREA_EP, "publicextract.charity_area_of_operation.json"
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
    df = data["CC_Area"]
    lkp = data["ltla_utla"]
    df = df[df["geographic_area_type"] == "Local Authority"]

    df = df[["geographic_area_description", "registered_charity_number"]]
    df = df.rename(
        columns={
            "geographic_area_description": "utla_name",
            "registered_charity_number": "count",
        }
    )
    df = (
        df.groupby("utla_name")
        .count()
        .sort_values("count", ascending=False)
        .reset_index()
    )

    # Charity commission do not use standard area codes, so clean them up
    df["utla_clean"] = df["utla_name"].apply(clean_utla_names)
    lkp["utla_clean"] = lkp["utla_name"].apply(clean_utla_names)

    df = df.merge(
        lkp, on="utla_clean", how="left", suffixes=("_cc", "_ons")
    ).drop_duplicates(subset=["utla_clean"])

    no_match = df["utla_code"].isnull()
    logging.warning(
        f"No matches for {[name for name in df.loc[no_match, 'utla_name_cc']]}"
    )

    # fill unmatched ons utla names with CC names, they don't have utla_codes
    df = df.rename(columns={"utla_name_ons": "utla_name"})
    df["utla_name"] = df["utla_name"].fillna(df["utla_name_cc"])

    df = df[["utla_code", "utla_name", "count"]]
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
        utla_pop,
        data["n_charities"],
        how="outer",
    )
    df["per_1000"] = 1000 * df["count"] / df["population"]
    df = df.sort_values("per_1000", ascending=False)
    return df


N_CHARITIES_UTLA = DataAsset(
    name="Number of charities operational by UTLA",
    inputs={"CC_Area": CC_AREA, "ltla_utla": LTLA_UTLA},
    processer=charities_by_la,
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
