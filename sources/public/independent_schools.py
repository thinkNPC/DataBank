from datetime import datetime

import pandas as pd

from models import DataDate, DataSource, DateMeta, Organisations, SourceType
from utils import CACHE

INDEPENDENT_SCHOOLS_URL = "https://raw.githubusercontent.com/drkane/charity-lookups/master/independent-schools-ew.csv"


@CACHE.memoize()
def get_ind_schools():
    return DataDate(
        pd.read_csv(INDEPENDENT_SCHOOLS_URL),
        DateMeta(publish_date=datetime.now().date()),
    )


INDEPENDENT_SCHOOLS = DataSource(
    name="Independent Schools",
    data_getter=get_ind_schools,
    org=Organisations.kanedata,
    source_type=SourceType.public_download,
    url="https://github.com/drkane/charity-lookups/blob/master/independent-schools-ew.csv",
    description="""
    List of Independent Schools with charity numbers
    """,
)
