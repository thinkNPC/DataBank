import logging

from assets import DATA_BANK_INPUTS
from partner.turn2us import Turn2us


logging.basicConfig(level=logging.WARNING)

def run_one(asset):
    print(asset)
    print(asset.get_data())

def run_all():
    for asset in DATA_BANK_INPUTS:
        print(asset)
        df = asset.get_data()
        logging.info(asset)
        logging.info(df.iloc[0].head())

if __name__ == "__main__":
    run_all()
