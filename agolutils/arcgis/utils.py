from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import dotenv_values
import arcgis
from arcgis.gis import GIS
from agolutils.config.config import load_config


def get_gis_from_env(env) -> GIS:
    config = dotenv_values(env)

    CRED = {
        "url": config.get("ARCGIS_URL", None),
        "username": config["ARCGIS_USERNAME"],
        "password": config["ARCGIS_PASSWORD"],
    }
    return GIS(**CRED)


def get_gis_from_config(config: Union[Dict, str, Path]) -> GIS:
    config = load_config(config)

    CRED = {
        "url": config.get("ARCGIS_URL", None),
        "username": config["ARCGIS_USERNAME"],
        "password": config["ARCGIS_PASSWORD"],
    }
    return GIS(**CRED)


def get_gis(
    config: Optional[Dict] = None, env: Optional[Union[str, Path]] = None
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


def get_layer_by_prop(obj: arcgis.gis.Item, prop: str, equals: Any):
    fxn = lambda x: x.properties.get(prop) == equals
    return next(filter(fxn, obj.layers + obj.tables))


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
    for dct in relates.values():
        fields = dct.get("__layer_properties", {}).get("fields", [])
        domain_fields = filter(domain_filter, fields)
        for field in domain_fields:
            name = field["name"]
            domain = field["domain"]
            mapping = {d["code"]: d["name"] for d in domain["codedValues"]}
            for data_dct in dct["data"]:
                data_dct[name + "__as_name"] = mapping.get(data_dct.get(name), "None")

    return context
