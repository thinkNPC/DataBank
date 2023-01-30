from functools import reduce

from partner import turn2us
from public import imd, census
from models import DataAsset, DataSource, DateMeta, SourceType, Organisations

import pandas as pd


def score_merge(data1, data2, dfm, col='la_code'):
    (key1, df1) = data1
    (key2, df2) = data2    
    set1 = set(df1[col])
    set2 = set(df2[col])
    setm = set(dfm[col])
    if (set1 == set2) and (set2 == setm):
        print(f'Merge success: ({key1})({key2})')
    else:
        print(f'Merge fail: ({key1})({key2})')
        print((set1 == set2), (set2 == setm))
        outer = set1 | set2
        set1_extra = set1 - set2
        set2_extra = set2 - set1
        print(f'set1 but not set2: {len(set1_extra)}, {set1_extra}')
        print(f'set2 but not set1: {len(set2_extra)}, {set2_extra}')



def combine_la(data1, data2):
    (key1, df1) = data1
    (key2, df2) = data2
    col = 'la_code'
    assert 'la_code' in df1.columns
    assert 'la_code' in df2.columns

    df = pd.merge(df1, df2, how='outer')
    score_merge(data1, data2, df)
    return ('combined', df)

def combine_datasets(data):
    (key, df) = reduce(combine_la, data.items())
    return df
    

DATA_BANK_INPUTS = (
    census.POP_LA,
    census.ETHNICITY_LA,
    imd.IMD_LA,
    turn2us.Turn2usProportional,
)

DataBank = DataAsset(
    'DataBank',
    inputs={asset.name: asset for asset in DATA_BANK_INPUTS},
    processer=combine_datasets,
)