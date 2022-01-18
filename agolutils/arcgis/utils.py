from pathlib import Path
from typing import Any, Dict, Optional, Union

from dotenv import dotenv_values
import arcgis
from arcgis.gis import GIS
from agolutils.config.config import load_config


def get_gis_from_env(env) -> GIS:
    config = dotenv_values(env)

    CRED = {
        "username": config["ARCGIS_USERNAME"],
        "password": config["ARCGIS_PASSWORD"],
    }
    return GIS(**CRED)


def get_gis_from_config(config: Union[Dict, str, Path]) -> GIS:

    config = load_config(config)

    CRED = {
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
    itemid: Optional[str] = None,
    config: Optional[Union[Dict, str, Path]] = None,
    env: Optional[Union[str, Path]] = None,
):
    config = load_config(config)
    gis = get_gis(config, env)
    if itemid is None:
        itemid = config.get("service_id")
    return gis.content.get(itemid)


def get_layer_by_prop(obj: arcgis.gis.Item, prop: str, equals: Any):
    fxn = lambda x: x.properties.get(prop) == equals
    return next(filter(fxn, obj.layers + obj.tables))
