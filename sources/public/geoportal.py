import functools
import io
import os

import pandas as pd
import requests

import utils
from models import (DataAsset, DataDate, DataSource, DateMeta, Organisations,
                    SourceType)

LTLA_UTLA_FILE = {
    "fname": "Lower_Tier_Local_Authority_to_Upper_Tier_Local_Authority_(December_2022)_Lookup_in_England_and_Wales.csv",
    "publish_date": pd.to_datetime("2022-12-01"),
}

LTLA_REGION_FILE = {
    "fname": "Local_Authority_District_to_Region_(December_2022)_Lookup_in_England.csv",
    "publish_date": pd.to_datetime("2022-12-01"),
}

LTLA_COUNTRY_FILE = {
    "fname": "Local_Authority_District_to_Country_(December_2022)_Lookup_in_the_United_Kingdom.csv",
    "publish_date": pd.to_datetime("2022-12-01"),
}


def get_ltla_region_lookup():
    path = os.path.join(utils.RESOURCE_DIR, LTLA_REGION_FILE["fname"])
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "LAD22CD": "la_code",
            "LAD22NM": "la_name",
            "RGN22CD": "region_code",
            "RGN22NM": "region_name",
        }
    )
    return DataDate(df, DateMeta(publish_date=LTLA_REGION_FILE["publish_date"]))


def get_ltla_country_lookup():
    path = os.path.join(utils.RESOURCE_DIR, LTLA_COUNTRY_FILE["fname"])
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "LAD22CD": "la_code",
            "LAD22NM": "la_name",
            "CTRY22CD": "country_code",
            "CTRY22NM": "country_name",
        }
    )
    return DataDate(df, DateMeta(publish_date=LTLA_COUNTRY_FILE["publish_date"]))


def get_ltla_utla_lookup():
    path = os.path.join(utils.RESOURCE_DIR, LTLA_UTLA_FILE["fname"])
    df = pd.read_csv(path)
    df = df.rename(
        columns={
            "LTLA22CD": "la_code",
            "LTLA22NM": "la_name",
            "UTLA22CD": "utla_code",
            "UTLA22NM": "utla_name",
        }
    )
    return DataDate(df, DateMeta(publish_date=LTLA_UTLA_FILE["publish_date"]))


def combine_lkps(data):
    def ons_merge(df1, df2):
        df = pd.merge(df1, df2, on="la_code", how="outer")
        df["la_name"] = df["la_name_x"].fillna(df["la_name_y"])
        df = df.drop(["la_name_x", "la_name_y"], axis=1)
        return df

    data = {key: df.drop("ObjectId", axis=1) for key, df in data.items()}
    df = functools.reduce(
        ons_merge,
        data.values(),
    )
    for suffix in ["_name", "_code"]:
        df[f"region{suffix}"] = df[f"region{suffix}"].fillna(df[f"country{suffix}"])
        df[f"utla{suffix}"] = df[f"utla{suffix}"].fillna(df[f"la{suffix}"])

    return df


LTLA_UTLA = DataSource(
    name="LTLA to UTLA",
    data_getter=get_ltla_utla_lookup,
    org=Organisations.ons,
    sub_org="GeoPortal",
    source_type=SourceType.public_download,
    url="https://geoportal.statistics.gov.uk/datasets/ons::lower-tier-local-authority-to-upper-tier-local-authority-december-2022-lookup-in-england-and-wales/explore",
    dateMeta=DateMeta(update_freq=utils.YEAR),
)

LTLA_REGION = DataSource(
    name="LTLA to Region",
    data_getter=get_ltla_region_lookup,
    org=Organisations.ons,
    sub_org="GeoPortal",
    source_type=SourceType.public_download,
    url="https://geoportal.statistics.gov.uk/datasets/ons::local-authority-district-to-country-december-2022-lookup-in-the-united-kingdom/explore",
    dateMeta=DateMeta(update_freq=utils.YEAR),
)

LTLA_COUNTRY = DataSource(
    name="LTLA to Country",
    data_getter=get_ltla_country_lookup,
    org=Organisations.ons,
    sub_org="GeoPortal",
    source_type=SourceType.public_download,
    url="https://geoportal.statistics.gov.uk/datasets/ons::local-authority-district-to-country-december-2022-lookup-in-the-united-kingdom/explore",
    dateMeta=DateMeta(update_freq=utils.YEAR),
)

LKP = DataAsset(
    name="LTLA/UTLA/Region/Country lookup",
    inputs={"utla": LTLA_UTLA, "region": LTLA_REGION, "country": LTLA_COUNTRY},
    processer=combine_lkps,
)
