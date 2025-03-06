import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import dotenv_values
from arcgis.gis import GIS, Item
from agolutils.config.config import load_config


class RedirectStdStreams(object):
    def __init__(self, stdout=None, stderr=None):
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush()
        self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush()
        self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


def _get_gis(dct):
    f = io.StringIO()

    with RedirectStdStreams(stdout=f, stderr=f):
        gis_connection = GIS(
            url=dct.get("ARCGIS_URL", None),
            username=dct["ARCGIS_USERNAME"],
            password=dct["ARCGIS_PASSWORD"],
            verify_cert=json.loads(dct.get("VERIFY_CERT", "true")),
        )
    s = f.getvalue().splitlines()
    for line in s:
        if "Setting `verify_cert` to False is a security risk".lower() in line.lower():
            continue
        print(line)

    return gis_connection


def get_gis_from_env(env) -> GIS:
    config = dotenv_values(env)

    return _get_gis(config)


def get_gis_from_config(config: Union[Dict, str, Path]) -> GIS:
    config = load_config(config)

    return _get_gis(config)


def get_gis(
    config: Optional[Union[Dict, str, Path]] = None,
    env: Optional[Union[str, Path]] = None,
) -> GIS:
    try:
        return get_gis_from_env(env)
    except FileNotFoundError:
        if config:
            return get_gis_from_config(config)
    raise ValueError("One of `config` or `env` is required.")


def get_content(
    itemid: str,
    config: Optional[Union[Dict, str, Path]] = None,
    env: Optional[Union[str, Path]] = None,
):
    config = load_config(config)
    gis = get_gis(config, env)

    return gis.content.get(itemid)


def get_layer_by_prop(obj: Item, prop: str, equals: Any):
    fxn = lambda x: x.properties.get(prop) == equals  # noqa: E731
    return next(filter(fxn, (obj.layers or []) + (obj.tables or [])))


def domain_filter(x):
    return (x.get("domain") is not None) and (
        x.get("domain", {}).get("type", None) == "codedValue"
    )


def remap_domains_as_name(context):
    fields = context.get("__layer_properties", {}).get("fields", [])
    domain_fields = filter(domain_filter, fields)
    for field in domain_fields:
        name = field["name"]
        domain = field["domain"]
        mapping = {d["code"]: d["name"] for d in domain["codedValues"]}
        context[name + "__as_name"] = mapping.get(context.get(name), "None")

    return context


def remap_related_domains_as_name(context):
    relates = context.get("relates", {})
    for relate in relates.values():
        for data_ctx in relate["data"]:
            remap_domains_as_name(data_ctx)

    return context
