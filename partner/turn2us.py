import os

import pandas as pd

from models import DataAsset, DataSource, DateMeta, Organisations, SourceType
from public.census import POP_LA
from utils import CACHE, DATA_DIR

TURN2US_DATA = {
    "fname": "08.07.2020 - Turn 2 Us Data.xlsx",
    "publish_date": pd.to_datetime("2020-07-08"),
}

TURN2US_LA_MATCH = {
    "Bournemouth": "E06000028",
    "Christchurch": "E07000048",
    "East Dorset": "E07000049",
    "North Dorset": "E07000050",
    "Poole": "E06000029",
    "Purbeck": "E07000051",
    "Taunton Deane": "E07000190",
    "West Dorset": "E07000052",
    "West Somerset": "E07000191",
    "Weymouth and Portland": "E07000053",
    "Aylesbury Vale": "E07000004",
    "Chiltern": "E07000005",
    "Shepway": "E07000112",
    "South Bucks": "E07000006",
    "Wycombe": "E07000007",
    "Forest Heath": "E07000201",
    "St Edmundsbury": "E07000204",
    "Waveney": "E07000206",
    "Suffolk Coastal": "E07000205",
    "Corby": "E07000150",
    "Daventry": "E07000151",
    "East Northamptonshire": "E07000152",
    "Kettering": "E07000153",
    "Northampton": "E07000154",
    "South Northamptonshire": "E07000155",
    "Wellingborough": "E07000156",
}


@CACHE.memoize()
def read_turn2us():
    path = os.path.join(DATA_DIR, TURN2US_DATA["fname"])
    df = pd.read_excel(path, parse_dates=["Application Date"])

    df = df.rename(columns={"Local Authority": "la_name"})
    ons_codes = POP_LA.get_data()[["la_code", "la_name"]]
    df = pd.merge(df, ons_codes, how="left")
    no_match = df["la_code"].isnull()
    df.loc[no_match, "la_code"] = df.loc[no_match, "la_name"].map(TURN2US_LA_MATCH)

    date_meta = DateMeta(
        publish_date=TURN2US_DATA["publish_date"],
        latest_date=df["Application Date"].max(),
    )
    return df, date_meta


def agg_turn2us_by_la(data):
    df = data["turn2us"]

    df = df.groupby(["la_name", "la_code"]).sum(numeric_only=True).reset_index()

    not_application_cols = [
        "la_name",
        "la_code",
        "Applications",
        "Application Date",
    ]
    application_cols = list(set(df.columns) - set(not_application_cols))
    df[application_cols] = df[application_cols].div(df["Applications"], axis=0)
    return df


Turn2us = DataSource(
    name="Turn2us - all applications",
    data_getter=read_turn2us,
    source_type=SourceType.email,
    org=Organisations.turn2us,
    description="",
    dateMeta=DateMeta(update_freq=pd.Timedelta("365 days")),
)


Turn2usProportional = DataAsset(
    name="Turn2us - all applications by LA",
    inputs={"turn2us": Turn2us},
    processer=agg_turn2us_by_la,
)
