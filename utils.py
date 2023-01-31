from diskcache import Cache

CACHE = Cache("cachedir")

DATA_DIR = 'data'
OUTPUT_DIR = 'output'


def drop_buckinghamshire_2020(df):
    # 4 LAs became E06000060/Buckinghamshire in 2020
    # https://l-hodge.github.io/ukgeog/articles/boundary-changes.html
    assert all(col in df.columns for col in ['la_code', 'la_name'])

    old_codes = ['E07000004', 'E07000005', 'E07000006', 'E07000007'] 
    df = df[~df['la_code'].isin(old_codes)]
    return df

def drop_northamptonshire_2021(df):
    assert all(col in df.columns for col in ['la_code', 'la_name'])

    changes = {
        'E06000061': ['E07000150', 'E07000152', 'E07000153', 'E07000156'],
        'E06000062': ['E07000151', 'E07000154', 'E07000155'],
    }
    old_codes = []
    for codes in changes.values():
        old_codes += codes
    df = df[~df['la_code'].isin(old_codes)]
    return df
