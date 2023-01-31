from sources.partner import turn2us
from sources.public import census, imd

DATA_BANK_INPUTS = (
    turn2us.Turn2usProportional,
    imd.IMD_LA,
    census.ETHNICITY_LA,
    census.AGE_SEX_LA,
    census.POP_LA,
)
