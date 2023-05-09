import models
from sources.partner import trusselltrust, turn2us
from sources.public import (
    census,
    charity_comission,
    imd,
    independent_schools,
    levellingup,
)

SummaryReport = models.Report(
    name="Report",
    assets=(
        charity_comission.CharityDensityHex,
        charity_comission.CharitySpendDensityHex,
        levellingup.LEVELLING_UP_HEX,
        levellingup.LEVELLING_UP_UTLA_HEX,
        charity_comission.CharitySpendLvlupStrip,
        charity_comission.CharitySpendLvlupHex,
        trusselltrust.TrussellTrustHex,
    ),
)


ASSETS = (
    turn2us.Turn2usProportional,
    imd.IMD_LA,
    census.ETHNICITY_LA,
    census.AGE_SEX_LA,
    census.POP_LA,
    charity_comission.CC_MAIN,
    independent_schools.INDEPENDENT_SCHOOLS,
    charity_comission.CC_AREA,
    charity_comission.CC_CATEGORY,
    charity_comission.CC_HISTORY,
    charity_comission.CC_GRANTMAKER,
    charity_comission.CC_HISTORY_AREA,
    charity_comission.LVL_UP_AREA_HISTORY,
    charity_comission.LVL_UP_AREA_HISTORY_CHART,
    charity_comission.CC_ACTIVE,
    charity_comission.CC_BY_AREA,
    charity_comission.N_CHARITIES_UTLA,
    charity_comission.NCharitiesUTLAPerHead,
    charity_comission.CharitySpendDensityHex,
    charity_comission.CharityDensityHex,
    charity_comission.CharitySpendLvlupStrip,
    charity_comission.CharitySpendLvlupHex,
    charity_comission.CC_3_AREAS,
    charity_comission.CC_3_AREAS_CHART,
    charity_comission.CC_SPEND_YEAR_UTLA,
    levellingup.LEVELLING_UP,
    levellingup.LVL_BY_UTLA,
    levellingup.LEVELLING_UP_HEX,
    trusselltrust.TrussellTrust,
    trusselltrust.TrussellTrustProportional,
    trusselltrust.TrussellTrustHex,
    SummaryReport,
)

ASSETS_DICT = {asset.name: asset for asset in ASSETS}


def all_sources():
    all_sources = []
    for key, asset in ASSETS_DICT.items():
        if isinstance(asset, models.DataSource):
            sources = [asset]
        else:
            sources = asset.sources
        for s in sources:
            if all(s.name != source.name for source in all_sources):
                all_sources.append(s)
    return all_sources
