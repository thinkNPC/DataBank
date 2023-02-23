import importlib
import logging
import sys
import traceback

import assets
import models
from combine import DataBank

logging.basicConfig(level=logging.INFO)


def run_asset(key):
    asset = assets.ASSETS_DICT[key]

    print("=" * 16)
    print(asset)
    try:
        models.Output(asset).to_file()
    except Exception:
        print(traceback.format_exc())
        print("Falure")
    else:
        print("Success")
    print("=" * 16)


def run_all_assets():
    for asset in assets.ASSETS_DICT:
        run_asset(asset)


def all_sources():
    for source in assets.all_sources():
        print(source)


def sources_up_to_date():
    for source in assets.all_sources():
        source.get_data()
        print(source.date_info)


if __name__ == "__main__":
    match sys.argv:
        case [main]:
            # some default behaviour
            run_asset("Charities spend by levelling up area hexmap")
        case [main, "source"]:
            all_sources()
        case [main, "source", "date"]:
            sources_up_to_date()
        case [main, "asset", "all"]:
            run_all_assets()
        case [main, "asset", *names]:
            print(names)
            for name in names:
                run_asset(name)
