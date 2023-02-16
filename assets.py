from models import Report
from reports import summary
from sources.partner import trusselltrust, turn2us
from sources.public import census, charity_comission, imd, levellingup

SummaryReport = Report(
    name="Report",
    assets=(
        charity_comission.CharityDensityHex,
        trusselltrust.TrussellTrustHex,
        levellingup.LEVELLING_UP_HEX,
    ),
)


ASSETS = (
    turn2us.Turn2usProportional,
    imd.IMD_LA,
    census.ETHNICITY_LA,
    census.AGE_SEX_LA,
    census.POP_LA,
    charity_comission.CharityDensityHex,
    levellingup.LEVELLING_UP,
    levellingup.LEVELLING_UP_HEX,
    trusselltrust.TrussellTrust,
    trusselltrust.TrussellTrustProportional,
    trusselltrust.TrussellTrustHex,
    SummaryReport,
)

ASSETS_DICT = {asset.name: asset for asset in ASSETS}
