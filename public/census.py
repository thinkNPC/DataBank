import os
import io
import pandas as pd
import requests
from models import DataAsset, DataSource, DateMeta, SourceType, Organisations
from utils import DATA_DIR

ONS_API_ENDPOINT = "https://api.beta.ons.gov.uk/v1/datasets/{id}"
ETHNICITY_ID = "TS021"
AGE_SEX_LA_ID = "TS009"

TEN_YEARS = pd.Timedelta(10 * 365, unit="days")

CENSUS_LA_COL_MAP = {
    "Lower Tier Local Authorities Code": "la_code",
    "Lower Tier Local Authorities": "la_name",
}


def get_ons_latest_df_and_date(id):
    dataset_info = requests.get(ONS_API_ENDPOINT.format(id=id))
    latest_dataset = requests.get(
        dataset_info.json()["links"]["latest_version"]["href"]
    )
    publish_date = pd.to_datetime(latest_dataset.json()["release_date"]).replace(
        tzinfo=None
    )
    csv_url = latest_dataset.json()["downloads"]["csv"]["href"]

    r = requests.get(csv_url)
    return pd.read_csv(io.StringIO(r.content.decode("utf-8"))), publish_date


def get_census_ethnicity():
    df, publish_date = get_ons_latest_df_and_date(ETHNICITY_ID)
    df = df.rename(columns=CENSUS_LA_COL_MAP)
    df = df.pivot(
        index=CENSUS_LA_COL_MAP.values(),
        columns="Ethnic group (20 categories)",
        values="Observation",
    ).reset_index()
    return df, DateMeta(publish_date=publish_date)


def get_census_age_sex():
    df, publish_date = get_ons_latest_df_and_date(AGE_SEX_LA_ID)
    df = df.rename(columns=CENSUS_LA_COL_MAP)
    return df, DateMeta(publish_date=publish_date)


def group_populations(data):
    df = data["age_sex_census"]
    la_cols = list(CENSUS_LA_COL_MAP.values())
    df = df[la_cols + ["Observation"]]
    df = df.groupby(la_cols).sum().reset_index()
    return df


ETHNICITY_LA = DataSource(
    name="Ethnicity populations by LA",
    data_getter=get_census_ethnicity,
    org=Organisations.ons,
    sub_org="Census2021",
    source_type=SourceType.api,
    url="https://census.gov.uk/",
    dateMeta=DateMeta(update_freq=TEN_YEARS),
)

AGE_SEX_LA = DataSource(
    name="LA populations: Sex by single year of age",
    data_getter=get_census_age_sex,
    org=Organisations.ons,
    sub_org="Census2021",
    source_type=SourceType.api,
    url="https://www.ons.gov.uk/datasets/TS009/editions/2021/versions/1",
    dateMeta=DateMeta(update_freq=TEN_YEARS),
)

POP_LA = DataAsset(
    name="LA populations",
    inputs={"age_sex_census": AGE_SEX_LA},
    processer=group_populations,
)
