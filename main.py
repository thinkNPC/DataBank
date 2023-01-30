import logging

from assets import DATA_BANK_INPUTS
from partner.turn2us import Turn2us
from public.imd import IMD_LA
from combine import DataBank

logging.basicConfig(level=logging.WARNING)

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
    #run_all()
    run_one(DataBank)


