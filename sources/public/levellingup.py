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
    df = pd.merge(df, LKP.get_data()[["la_code", "la_name"]], how="left")
    return DataDate(df, DateMeta(publish_date=LEVELLING_UP_AREAS["publish_date"]))


def levelling_up_map(data):
    df = data["lvlup"]
    fig = hex.plot_hexes(df, "LTLA", "Category", palette="magma")
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

LEVELLING_UP_HEX = DataAsset(
    name="Hexmap of levelling up areas",
    inputs={
        "lvlup": LEVELLING_UP,
    },
    processer=levelling_up_map,
)
