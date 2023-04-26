import os

import pandas as pd

from models import DataAsset, DataDate, DataSource, DateMeta, Organisations, SourceType
from plotting import hex
from sources.public.census import POP_LA
from utils import CACHE, DATA_DIR

TT_DATA = {
    "fname": "Trussell Trust - just LA 2022.xlsx",
    "publish_date": pd.to_datetime("2022-04-01"),
    "latest_date": pd.to_datetime("2022-03-31"),
}

TT_COLS = [
    "Number of parcels given to adults",
    "Number of parcels given to children",
    "Total number of parcels distributed",
    "Number of distribution centres",
]


@CACHE.memoize()
def read_trusselltrust():
    path = os.path.join(DATA_DIR, TT_DATA["fname"])
    df = pd.read_excel(path)

    df = df.rename(columns={"Local Authority": "la_name"})
    ons_codes = POP_LA.get_data()[["la_code", "la_name"]]
    df = pd.merge(df, ons_codes, how="left")

    date_meta = DateMeta(
        publish_date=TT_DATA["publish_date"],
        latest_date=TT_DATA["latest_date"],
    )
    return DataDate(df, date_meta)


def normalise_trussell_data(data):
    df = data["trussell"]  # .dropna(subset=['la_code'])
    pop = POP_LA.get_data()[["la_code", "population"]]
    df = pd.merge(df, pop)
    df[TT_COLS] = df[TT_COLS].divide(df["population"], axis=0)
    df = df.sort_values("Total number of parcels distributed", ascending=False)
    return df


TrussellTrust = DataSource(
    name="Trussell Trust data return",
    data_getter=read_trusselltrust,
    source_type=SourceType.email,
    org=Organisations.trussell_trust,
    description="Food parcels delivered by local authority",
    dateMeta=DateMeta(update_freq=pd.Timedelta("365 days")),
)

TrussellTrustProportional = DataAsset(
    name="Trussell trust per head",
    inputs={"trussell": TrussellTrust},
    processer=normalise_trussell_data,
)


def trussell_hex(data):
    df = data["trussell"]
    fig = hex.plot_hexes(df, "LTLA", "Total number of parcels distributed")
    return fig


TrussellTrustHex = DataAsset(
    name="Trussell parcels delivered per head",
    inputs={
        "trussell": TrussellTrustProportional,
    },
    processer=trussell_hex,
)
