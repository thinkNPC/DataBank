from sources.partner import trusselltrust, turn2us
from sources.public import census, charity_comission, imd

ASSETS = (
    turn2us.Turn2usProportional,
    imd.IMD_LA,
    census.ETHNICITY_LA,
    census.AGE_SEX_LA,
    census.POP_LA,
    charity_comission.CharityDensityHex,
    trusselltrust.TrussellTrust,
    trusselltrust.TrussellTrustProportional,
    trusselltrust.TrussellTrustHex,
)

ASSETS_DICT = {asset.name: asset for asset in ASSETS}

REPORT = (
    trusselltrust.TrussellTrustHex,
    # charity_comission.CharityDensityHex,
)
