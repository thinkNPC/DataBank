from sources.partner import turn2us, trusselltrust
from sources.public import census, imd

ASSETS = (
    turn2us.Turn2usProportional,
    imd.IMD_LA,
    census.ETHNICITY_LA,
    census.AGE_SEX_LA,
    census.POP_LA,
    trusselltrust.TrussellTrust,
    trusselltrust.TrussellTrustProportional,
    trusselltrust.TrussellTrustHex,
)

ASSETS_DICT = {
    asset.name: asset for asset in ASSETS
}
