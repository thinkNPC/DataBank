import io
import os

import pandas as pd
import requests

from models import DataDate, DataAsset, DataSource, DateMeta, Organisations, SourceType
import utils

LTLA_UTLA_FILE = {
    "fname": "Lower_Tier_Local_Authority_to_Upper_Tier_Local_Authority_(December_2022)_Lookup_in_England_and_Wales.csv",
    "publish_date": pd.to_datetime("2022-12-01"),
}

def get_ltla_utla_lookup():
    path = os.path.join(utils.RESOURCE_DIR, LTLA_UTLA_FILE['fname'])
    df = pd.read_csv(path)
    df = df.rename(columns={
        'LTLA22CD': 'la_code',
        'LTLA22NM': 'la_name',
        'UTLA22CD': 'utla_code',
        'UTLA22NM': 'utla_name',
    })
    return DataDate(df, DateMeta(publish_date=LTLA_UTLA_FILE["publish_date"]))
    

LTLA_UTLA = DataSource(
    name="LTLA to UTLA",
    data_getter=get_ltla_utla_lookup,
    org=Organisations.ons,
    sub_org="GeoPortal",
    source_type=SourceType.public_download,
    url="https://geoportal.statistics.gov.uk/datasets/ons::lower-tier-local-authority-to-upper-tier-local-authority-december-2022-lookup-in-england-and-wales/explore",
    dateMeta=DateMeta(update_freq=utils.YEAR),
)

