from functools import reduce
import logging

from partner import turn2us
from public import imd, census
from models import DataAsset, DataSource, DateMeta, SourceType, Organisations

import pandas as pd

SCORE_DEBUG = False

def score_merge(data1, data2, dfm, col='la_code'):
    (key1, df1) = data1
    (key2, df2) = data2   

    N = len(df1)
    unique_cols = set(df2.columns) - set(df1.columns)
    unique_col = list(unique_cols)[0]
    achieved = sum(dfm[unique_col].notnull())
    score = 100 * achieved / N
    if achieved != N:
        logging.warning(f'Merging: {key2}: {achieved} / {N} ({score:.0f}%)')
    else:
        logging.info(f'Merging: {key2}: {achieved} / {N} ({score:.0f}%)')

    if SCORE_DEBUG:
        set1 = set(df1[col])
        set2 = set(df2[col])
        setm = set(dfm[col])
        if (set1 == set2) and (set2 == setm):
            logging.info(f'Merge success: ({key1})({key2})')
        else:
            logging.warning(f'Merge fail: ({key1})({key2})')
            set1_extra = set1 - set2
            set2_extra = set2 - set1
            logging.warning(f'in left but not right: {len(set1_extra)}, {set1_extra}')
            logging.warning(f'in right but not left: {len(set2_extra)}, {set2_extra}')
            logging.warning(len(df1[col]), len(df2[col]), len(dfm[col]))
        logging.info()




def combine_la(data1, data2):
    (key1, df1) = data1
    (key2, df2) = data2
    col = 'la_code'
    assert 'la_code' in df1.columns
    assert 'la_code' in df2.columns

    df = pd.merge(df1, df2, how='left')
    score_merge(data1, data2, df)
    return ('combined', df)

def combine_databank_datasets(data):
    assert list(data.keys())[0] == 'LA populations'
    (_, df) = reduce(combine_la, data.items())
    return df
    

DATA_BANK_INPUTS = (
    census.POP_LA, # this must be the first item
    census.ETHNICITY_LA,
    imd.IMD_LA,
    turn2us.Turn2usProportional,
)

DataBank = DataAsset(
    'DataBank',
    inputs={asset.name: asset for asset in DATA_BANK_INPUTS},
    processer=combine_databank_datasets,
)