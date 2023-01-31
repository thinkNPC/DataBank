from functools import partial
import io
import pandas as pd
import requests
import zipfile
import json

from models import DataAsset, DataDate, DataSource, DateMeta, Organisations, SourceType
from utils import DATA_DIR, CACHE
from sources.public.census import POP_LA

CC_ENDPOINT = 'https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity.zip'
CC_AREA_EP = 'https://ccewuksprdoneregsadata1.blob.core.windows.net/data/json/publicextract.charity_area_of_operation.zip'

APPROX_MONTH = pd.Timedelta('31 days')

@CACHE.memoize()
def get_charity_commission_dataset(endpoint, fname):
    r = requests.get(endpoint)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        with z.open(fname)  as f:
            data = json.load(f)
    date = data[0]['date_of_extract']
    assert all([date == entry['date_of_extract'] for entry in data])

    df = pd.DataFrame.from_dict(data)
    date = pd.to_datetime(date)
    return DataDate(df, DateMeta(publish_date=date))

def get_cc_area():
    return get_charity_commission_dataset(
        CC_AREA_EP,
        'publicextract.charity_area_of_operation.json'
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
    """
)

def charities_by_la(data):
    df = data['CC_Area']
    df = df[df['geographic_area_type'] == 'Local Authority']

    df = df[['geographic_area_description', 'registered_charity_number']]
    df = df.rename(columns={
        'geographic_area_description': 'la_name',
        'registered_charity_number': 'count',
    })
    df = df.groupby('la_name').count().sort_values('count', ascending=False).reset_index()

    ons_codes = POP_LA.get_data()[["la_code", "la_name"]]
    print(len(df))
    df = pd.merge(df, ons_codes, how="outer")
    print(len(df), len(ons_codes))
    no_match = df["la_code"].isnull()
    print(df[no_match])
    #df.loc[no_match, "la_code"] = df.loc[no_match, "la_name"].map(TURN2US_LA_MATCH)

    return df

N_CHARITIES_LA = DataAsset(
    name='Charity operational LA',
    inputs={'CC_Area': CC_AREA},
    processer=charities_by_la,
)
