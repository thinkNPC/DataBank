import os
import pandas as pd
from models import DataAsset, DataSource, DateMeta, SourceType, Organisations
import utils

IMD_PUBLISH_URL = "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019"
IMD_LA_URL = 'https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/833995/File_10_-_IoD2019_Local_Authority_District_Summaries__lower-tier__.xlsx'

IMD_COL_MAP = {
    'Local Authority District code (2019)': 'la_code',
    'Local Authority District name (2019)': 'la_name',
}

def read_imd_la():
    df = pd.read_excel(IMD_LA_URL, sheet_name='IMD')
    df = df.rename(columns=IMD_COL_MAP)
    print(df)
    print(df.columns)
    df = utils.drop_buckinghamshire_2020(df)
    df = utils.drop_northamptonshire_2021(df)
    return df, DateMeta(
        publish_date=pd.to_datetime('2019-01-01'),
        update_freq=pd.Timedelta(365*5, unit='days'), # website says update due in 2023
    )


IMD_LA = DataSource(
    name="Top level IMD indicators by LA",
    data_getter=read_imd_la,
    org=Organisations.mhclg,
    sub_org="English indices of deprivation 2019",
    source_type=SourceType.webscrape,
    url=IMD_PUBLISH_URL,
    instructions='MHCLG website indicates indices are due to be updated in 2023',
)