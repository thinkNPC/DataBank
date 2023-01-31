import logging

from assets import DATA_BANK_INPUTS
from combine import DataBank
from models import Output
from sources.partner.turn2us import Turn2usProportional
from sources.public.imd import IMD_LA

logging.basicConfig(level=logging.INFO)


def run_databank():
    logging.info(DataBank)
    Output(DataBank).csv()


def run_one(asset):
    print(asset)
    df = asset.get_data()
    print(df)


def run_all():
    for asset in DATA_BANK_INPUTS:
        print(asset)
        df = asset.get_data()
        logging.info(asset)
        logging.info(df.iloc[0].head())


if __name__ == "__main__":
    run_databank()
