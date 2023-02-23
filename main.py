import importlib
import logging
import sys

import assets
from combine import DataBank
import models

logging.basicConfig(level=logging.INFO)


def run_databank():
    logging.info(DataBank)
    Output(DataBank).csv()


def run_all():
    for asset in DATA_BANK_INPUTS:
        print(asset)
        df = asset.get_data()
        logging.info(asset)
        logging.info(df.iloc[0].head())


def all_sources():
    for source in assets.all_sources():
        print(source)


def sources_up_to_date():
    for source in assets.all_sources():
        source.get_data()
        print(source.date_info)

    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        key = sys.argv[1]
        if key == 'sources':
            all_sources()
        elif key == 'sources_up_to_date':
            sources_up_to_date()
        else:
            asset = assets.ASSETS_DICT[key]
            print(asset.name)
            models.Output(asset).to_file()
