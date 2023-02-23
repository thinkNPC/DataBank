import logging
import os
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import plotly
import slugify

from utils import OUTPUT_DIR

DATE_FMT = "%d %b %Y"


class Organisations(Enum):
    turn2us = "Turn2us"
    mhclg = "Ministry of Housing, Communities & Local Government"
    ons = "Office for National Statistics"
    charity_commission = "Charity Commission"
    trussell_trust = "Trussell Trust"
    dluhc = "Department for Levelling Up, Housing and Communities"
    none = None


class SourceType(Enum):
    api = "API"
    webscrape = "Web scrape"
    public_download = "Public download"
    email = "Email return"


class DateMeta:
    def __init__(
        self,
        update_freq: pd.Timedelta | None = None,
        latest_date: pd.Timestamp | None = None,
        publish_date: pd.Timestamp | None = None,
        expected_lag: pd.Timedelta | None = None,
    ):
        self.update_freq = update_freq
        self.latest_date = latest_date
        self.publish_date = publish_date
        self.expected_lag = expected_lag
        self.date_keys = ["update_freq", "latest_date", "publish_date", "expected_lag"]
        self.update_str = ""

    def update(self, dateUpdate):
        for key in self.date_keys:
            old = getattr(self, key)
            new = getattr(dateUpdate, key)
            assert (old is None) or (
                new is None
            ), f"{key} is trying to be updated but is already set"
            if new:
                setattr(self, key, new)

    def validate(self, name):
        all_defined = all([bool(getattr(self, date)) for date in self.date_keys])
        checked = False
        validity = None

        # check if publish date is too old
        if self.publish_date and self.update_freq:
            update_due = self.publish_date + self.update_freq
            if update_due < pd.Timestamp.today():
                logging.warning(
                    f"Overdue data update: '{name}' was due an update on {update_due}."
                )
                logging.debug(self)
                validity = False
            else:
                validity = True
            checked = True

        # check if latest data date is too lagged
        if all([self.latest_date, self.expected_lag]):
            lag = self.publish_date - self.latest_date
            if lag > self.expected_lag:
                logging.warning(
                    f"Data is lagged more than expected: {name}, {self}, measured_lag={lag}."
                )
                logging.debug(self)
                validity = False
            else:
                validity = True
            checked = True

        if not checked:
            for key in self.date_keys:
                if getattr(self, key) is None:
                    logging.warning(
                        f"Unable to check for updates: Date object for '{name}'.{key} not set. {self}"
                    )
                    logging.debug(self)
                    validity = None

        return validity

    def __repr__(self):
        dates = {key: getattr(self, key) for key in self.date_keys}
        return f"DateMeta({dates})"


@dataclass
class DataDate:
    df: pd.DataFrame
    dateMeta: DateMeta


@dataclass
class DataSource:
    name: str
    source_type: SourceType
    data_getter: callable
    url: str = ""  # a human friendly url
    org: Organisations = Organisations.none
    sub_org: str = ""
    instructions: str = ""
    description: str = ""
    dateMeta: DateMeta = DateMeta()
    data: pd.DataFrame | None = None

    def get_data(self):
        if self.data is not None:
            return self.data

        dataDate = self.data_getter()
        assert (
            type(dataDate) is DataDate
        ), f"DataSource({self.name}).data_getter must return a DataDate object"

        self.dateMeta.update(dataDate.dateMeta)
        self.dateMeta.validate(self.name)
        self.data = dataDate.df
        return self.data

    @property
    def date_info(self):
        valid = self.dateMeta.validate(self.name)

        if valid is True:
            message = "up to date"
        elif valid is False:
            message = "due update"  
        elif valid is None:
            message = "no update info"
        else:
            raise RuntimeError
        
        output = f"{self.name} ({message}): "
        if self.dateMeta.latest_date:
            output += (
                f"latest data from: {self.dateMeta.latest_date.strftime(DATE_FMT)}; "
            )
        if self.dateMeta.publish_date:
            output += f"published on: {self.dateMeta.publish_date.strftime(DATE_FMT)}."
        return output

    def __repr__(self):
        return f"DataSource({self.name})"


class DataAsset:
    def __init__(
        self,
        name: str,
        description: str = "",
        inputs: dict = {},
        processer=None,
    ):
        self.name = name
        self.description = description
        self.inputs = inputs
        self.sources = self.collect_sources(inputs)
        self.processer = processer

    def get_data(self):
        data = {key: i.get_data() for key, i in self.inputs.items()}
        data = self.processer(data)
        return data

    def collect_sources(self, inputs):
        sources = []
        stack = list(inputs.values())
        while stack:
            input_ = stack.pop()
            if type(input_) is DataAsset:
                stack.extend(list(input_.inputs.values()))
            elif type(input_) is DataSource:
                if input_.name not in [source.name for source in sources]:
                    sources.append(input_)
            else:
                raise RuntimeError
        return sources

    @property
    def date_updated_str(self):
        dates = [source.date_info for source in self.sources]
        return " ".join(dates)

    def __repr__(self):
        return f"DataAsset({self.name}, sources: {[source.name for source in self.sources]})"


@dataclass
class Report:
    name: str
    assets: tuple

    def get_data(self):
        title = f"# {self.name}"
        content = [Output(asset).to_md_str() for asset in self.assets]
        return "\n\n".join([title] + content)


class Output:
    def __init__(self, asset):
        self.asset = asset

    def to_md_str(self):
        path = self.to_file()
        # point to output file as report will be there too
        # TODO group files needed for report into a dir
        splitpath = os.path.normpath(path).split(os.sep)
        if path.endswith("html"):
            with open(path) as f:
                content = f.read()
        elif path.endswith('png'):
            subpath = os.path.join(*splitpath[1:])
            content = f"![{self.asset.name}]({subpath})"
        else:
            assert RuntimeError('Not a valid markdown asset', self.asset)

        lines = [
            f"## {self.asset.name}",
            content,
            self.asset.description,
            f"Source: {self.asset.date_updated_str}",
        ]
        return "\n\n".join(lines)

    def to_file(self):
        output = self.asset.get_data()
        fname = slugify.slugify(self.asset.name)
        if isinstance(output, pd.DataFrame):
            path = self.write(output, fname, "csv", self.csv)
        elif isinstance(output, plotly.graph_objects.Figure):
            path = self.write(output, fname, "html", self.plotly_html)
            path = self.write(output, fname, "png", self.plotly_png)
        elif isinstance(output, str):
            path = self.write(output, fname, "md", self.md)
        else:
            raise RuntimeError(
                f"unrecognised asset data type {type(output)} from {self.asset}"
            )
        return path

    def write(self, output, fname, suffix, writer):
        path = os.path.join(OUTPUT_DIR, f"{fname}.{suffix}")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        writer(output, path)
        print(f"{self.asset.name} written to {path}")
        return path

    def csv(self, df, path):
        df.to_csv(path)

    def plotly_html(self, fig, path):
        fig.write_html(path, full_html=False, include_plotlyjs='cdn')

    def plotly_png(self, fig, path):
        fig.write_image(path, scale=3)

    def md(self, string, path):
        with open(path, "w") as f:
            f.write(string)
