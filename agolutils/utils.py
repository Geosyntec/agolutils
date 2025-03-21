import datetime
import importlib.machinery
import importlib.util
from pathlib import Path

from pytz import timezone


def null_plugin(context, cfg):
    return context, cfg


def get_plugin(config):
    plugin = config.get("plugin")

    if not plugin:
        return null_plugin

    _localpath = config["__config_relpath"] / (plugin + ".py")

    if _localpath.is_file():
        loader = importlib.machinery.SourceFileLoader(plugin, str(_localpath))
        spec = importlib.util.spec_from_loader(plugin, loader)
        if spec is not None:
            mod = importlib.util.module_from_spec(spec)
            loader.exec_module(mod)
            return mod.main

    try:
        mod = importlib.import_module(plugin)
        return mod.main
    except ModuleNotFoundError:
        pass

    try:
        mod = importlib.import_module("agolutils.plugins" + "." + plugin)
        return mod.main
    except ModuleNotFoundError:
        pass

    return null_plugin


def collect_files(filepaths):
    collected_files = []
    for file in filepaths:
        path = Path(file)
        if path.is_dir():
            collected_files.extend([str(p) for p in path.glob("*")])
        elif path.is_file():
            collected_files.append(str(path))
        else:
            raise ValueError("must be a directory or a file")
    return collected_files


def search_files(patterns):
    found = []
    for p in patterns:
        found.extend([x.resolve() for x in Path(".").glob(p)])
    return found


def make_dir(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def make_path(filepath):
    path = Path(filepath)
    make_dir(path.parent)
    return path


## Datetime Formatters
PRESETS = {
    "date_time": "%m/%d/%Y %I:%M %p %Z",
    "date_time_military": "%m/%d/%Y %H:%M %Z",
    "date_time_ts_ms": "%Y-%m-%d_%H-%M-%S-%f",
    "date_time_ts": "%Y-%m-%d_%H-%M-%S",
    "date": "%m/%d/%Y",
    "date_ts": "%Y-%m-%d",
    "query": "%Y-%m-%d %H:%M:%S",
    "time": "%I:%M %p %Z",
}


def format_date(timestamp, tz_string=None, fmt=None):
    """
    format AGOL timestamps in a variety of useful string formats
    timestamp : (int) timestamp from AGOL
    tz_string : (string) for timezone at the location of data collection
    fmt : (string) either name of preset, or valid formatting string for
        datetime.strftime(fmt)
    """

    if tz_string is None:
        tz_string = "UTC"

    utc_dt = datetime.datetime.fromtimestamp(timestamp, tz=timezone("UTC"))

    if fmt in PRESETS:
        return utc_dt.astimezone(timezone(tz_string)).strftime(
            PRESETS[fmt]  # type: ignore
        )

    elif fmt is not None:
        return utc_dt.astimezone(timezone(tz_string)).strftime(fmt)

    else:
        return utc_dt


tomorrow = lambda: (  # noqa: E731
    datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(1)
).strftime("%Y-%m-%d")

yesterday = lambda: (  # noqa: E731
    datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(1)
).strftime("%Y-%m-%d")
