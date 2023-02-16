import importlib
import logging
import sys

from assets import ASSETS_DICT
from combine import DataBank
from models import Output

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


def report(fname):
    with open(fname, "w") as f:
        f.write("# Example DataBank report\n\n")
        for asset in REPORT:
            f.write(Output(asset).to_md_str())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asset = ASSETS_DICT[sys.argv[1]]
        print(asset.name)
        print(asset.get_data())
        Output(asset).to_file()
