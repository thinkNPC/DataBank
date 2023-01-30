import os
import pandas as pd
from models import DataAsset, DataSource, DateMeta, SourceType, Organisations
from utils import DATA_DIR, CACHE

TURN2US_DATA = {
    'fname': '08.07.2020 - Turn 2 Us Data.xlsx',
    'publish_date': pd.to_datetime('2020-07-08'),
}



@CACHE.memoize()
def read_turn2us():
    path = os.path.join(DATA_DIR, TURN2US_DATA['fname'])
    data = pd.read_excel(path, parse_dates=['Application Date'])
    date_meta = DateMeta(
        publish_date=TURN2US_DATA['publish_date'],
        latest_date=data['Application Date'].max(),
    )
    return data, date_meta


def agg_turn2us_by_la(data):
    df = data['turn2us']
    df_sum = df.groupby('Local Authority').sum(numeric_only=True)
    df_region = df[['Local Authority', 'Region']].groupby('Local Authority').agg(pd.Series.mode)
    df = pd.merge(df_sum, df_region, left_index=True, right_index=True, how='outer').reset_index()

    not_application_cols = [
        'Local Authority',
        'Applications',
        'Application Date',
        'Region'
    ]
    application_cols = list(set(df.columns) - set(not_application_cols))
    df[application_cols] = df[application_cols].div(df['Applications'], axis=0)
    return df


Turn2us = DataSource(
    name="Turn2us - all applications",
    data_getter=read_turn2us,
    source_type=SourceType.email,
    org=Organisations.turn2us,
    description='',
    dateMeta=DateMeta(update_freq=pd.Timedelta('365 days')),
)


Turn2usProportional = DataAsset(
    name="Turn2us - all applications by LA",
    inputs={'turn2us': Turn2us},
    processer=agg_turn2us_by_la,
)
