import logging
import os
from dataclasses import dataclass
from enum import Enum

import pandas as pd
import slugify

from utils import OUTPUT_DIR


class Organisations(Enum):
    turn2us = "Turn2us"
    mhclg = "Ministry of Housing, Communities & Local Government"
    ons = "Office for National Statistics"
    none = None


class SourceType(Enum):
    api = ("API",)
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

        # check if publish date is too old
        if self.publish_date and self.update_freq:
            update_due = self.publish_date + self.update_freq
            if update_due < pd.Timestamp.today():
                logging.warning(
                    f"Overdue data update: '{name}' was due an update on {update_due}."
                )
                logging.debug(self)
            checked = True

        # check if latest data date is too lagged
        if all([self.latest_date, self.expected_lag]):
            lag = self.publish_date - self.latest_date
            if lag > self.expected_lag:
                logging.warning(
                    f"Data is lagged more than expected: {name}, {self}, measured_lag={lag}."
                )
                logging.debug(self)
            checked = True

        if not checked:
            for key in self.date_keys:
                if getattr(self, key) is None:
                    logging.warning(
                        f"Unable to check for updates: Date object for '{name}'.{key} not set. {self}"
                    )
                    logging.debug(self)

    def __repr__(self):
        dates = {key: getattr(self, key) for key in self.date_keys}
        return f"DateMeta({dates})"


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

        data, dateUpdate = self.data_getter()
        self.dateMeta.update(dateUpdate)
        self.dateMeta.validate(self.name)
        self.data = data
        return data

    def __repr__(self):
        return f"DataSource({self.name})"


class DataAsset:
    def __init__(
        self,
        name: str,
        inputs: dict = {},
        processer=None,
    ):
        self.name = name
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

    def __repr__(self):
        return f"DataAsset({self.name}, sources: {[source.name for source in self.sources]})"


class Output:
    def __init__(self, asset):
        self.asset = asset

    def csv(self):
        df = self.asset.get_data()
        fname = slugify.slugify(self.asset.name)
        path = os.path.join(OUTPUT_DIR, f"{fname}.csv")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df.to_csv(path)
        print(f"{self.asset.name} written to {path}")
