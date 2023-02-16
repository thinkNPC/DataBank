from models import Report
from reports import summary
from sources.partner import trusselltrust, turn2us
from sources.public import census, charity_comission, imd

SummaryReport = Report(
    name="Example summary report",
    assets=(trusselltrust.TrussellTrustHex,),
)


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
    SummaryReport,
)

ASSETS_DICT = {asset.name: asset for asset in ASSETS}
