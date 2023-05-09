# NPC data repository

This is an overngineered repository to bring in data sources, and create different assets. With functionality for tracking whether an asset and sources are up to date.

There are three key classes defined in `models.py`:

- DataDate: a dataclass consisting of a pandas dataframe and date information that tracks when the data was published, the latest datapoint, expected lag and expected update frequency
- DataSource: ingests data and returns a DataDate
- DataAsset: performs some transformation on DataSource(s)

You can define DataSources and DataAssets anywhere in the code, if you want to use them you need to collect it into ASSETTS in `assets.py`. To run an asset:

```
python main.py asset <name of asset>
```

To see all the sources used and whether they are up to date:

```
python main.py source
python main.py source date
```

Full usage in `main.py`.

Most data sources are pulled from API or webscraped. Data in `./sources/partner/` is held in the Local Needs Databank folder on the NPC OneDrive. Copy relevant files into `./data/`

## Levelling up analysis

Expenditure by levelling up areas:

```
python main.py asset "Charity expenditure per head in each local authority hexmap" "Charities spend by levelling up area violin plot" "Number of charities operational by UTLA per head" "Charities per 1000 people in each local authority hexmap" "Charities spend by levelling up area hexmap" "Expenditure by levelling up area over time" "Chart of expenditure by levelling up area over time" "3 focus areas data" "Area spend by year table"
```