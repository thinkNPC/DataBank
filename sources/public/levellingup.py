import pandas as pd

from models import (DataAsset, DataDate, DataSource, DateMeta, Organisations,
                    SourceType)
from plotting import hex
from sources.public.geoportal import LKP
from utils import YEAR

LEVELLING_UP_AREAS = {
    "url": "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1062538/Levelling_Up_Fund_round_2_-_list_of_local_authorites_by_priority_category.xlsx",
    "publish_date": pd.to_datetime("2022-03-22"),
}


def read_levelling_up_areas():
    df = pd.read_excel(LEVELLING_UP_AREAS["url"], sheet_name=0)
    df = df.rename(columns={"Local authority ": "la_name"})
    df['la_name'] = df['la_name'].str.replace('Rhondda Cynon Taf', ' Rhondda Cynon Taff')
    df = pd.merge(df, LKP.get_data()[["la_code", "la_name"]], how="left")
    return DataDate(df, DateMeta(publish_date=LEVELLING_UP_AREAS["publish_date"]))


def levelling_up_map(data):
    df = data["lvlup"]
    fig = hex.plot_hexes(df, "LTLA", "Category", palette="magma")
    return fig

def group_lvlup_to_utla(data):
    df = pd.merge(
        data['lvlup'],
        data['lkp'][['la_code', 'utla_name', 'utla_code']],
        how='outer',
    )
    df = df.groupby(['utla_code', 'utla_name']).mean()
    df = df.sort_values('Category')
    return df.reset_index()

def levelling_up_utla_map(data):
    df = data["lvlup"]
    df['Category'] = df['Category'].round(0)
    fig = hex.plot_hexes(df, "UTLA", "Category", palette="magma")
    return fig

LEVELLING_UP = DataSource(
    name="Levelling up priority categories",
    data_getter=read_levelling_up_areas,
    org=Organisations.dluhc,
    source_type=SourceType.webscrape,
    url="https://www.gov.uk/government/publications/levelling-up-fund-round-2-updates-to-the-index-of-priority-places",
    dateMeta=DateMeta(update_freq=YEAR),
    instructions="""
    Spreadsheet can be found under 'Levelling Up Fund Round 2: list of local authorities by priority category'"
    """,
)

LVL_BY_UTLA = DataAsset(
    name="Levelling up grouped up to UTLAs",
    inputs={
        "lvlup": LEVELLING_UP,
        'lkp': LKP,
    },
    processer=group_lvlup_to_utla,
)

LEVELLING_UP_HEX = DataAsset(
    name="Hexmap of levelling up areas",
    inputs={
        "lvlup": LEVELLING_UP,
    },
    processer=levelling_up_map,
)

LEVELLING_UP_UTLA_HEX = DataAsset(
    name="Hexmap of levelling up areas averaged across UTLAs",
    inputs={
        "lvlup": LVL_BY_UTLA,
    },
    processer=levelling_up_utla_map,
    description=(
        'Levelling up priority categories are calculated by LTLA. '
        'The average levelling up category in UTLA is shown here, '
        'rounded to the nearest whole number'
    )
)


