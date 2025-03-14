import json

import yaml


def load_yaml(filepath):
    with open(filepath) as f:
        contents = yaml.safe_load(f)
    return contents


def load_json(filepath):
    with open(filepath) as f:
        contents = json.load(f)
    return contents
