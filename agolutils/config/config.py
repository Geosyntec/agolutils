from pathlib import Path
from typing import Any, Dict, Optional, Union

import typer

from agolutils.io import load_yaml

config_file = """## Default Project Configuration ##

name: pc-gi-lid-inspections
service_id: bc2dbc566fdd410590f8369613f2642a

# *_file_patterns are completed with the values from the given context.
# e.g., if your context has a key with `globalid` as string and `EditDate` as int, 
# a directory will be created for the context and its related data at a new path with those 
# values filled from the context.
context_file_pattern: pc-gi-lid-inspections/contexts/{globalid}_editdate_{EditDate}/context.json
report_file_pattern: pc-gi-lid-inspections/reports/pc-gi-lid-inspections_{globalid}_{EditDate}.docx

# enter the timezone for report datetime stamp normalization.
report_tz: US/Eastern

# run `main` function from plugin prior to rendering the context
# this will load a ".py" file with the same name from the same directory as this config file
# or this will load the module with the same name from the plugins directory of this agolutils library
plugin: demo

docxtpl:
  template_filepath: templates/template.docx
  image:
    - key: images # list of dicts in context
      filepath_key: image_filepath # each dict in the `images` must contain a filepath key.
      max-width: 3
      max-height: 2
      units: inches # units of the max-width and height values. Allowed values are 'mm' and 'inches'.

"""


def load_config(config: Optional[Union[Dict, str, Path]] = None) -> Dict[str, Any]:

    if isinstance(config, dict):
        assert "__config_relpath" in config
        return config

    if not config:
        config = "./config.yml"

    elif isinstance(config, (str, Path)):
        path = Path(config).parent.resolve()
        config = load_yaml(config)
        config["__config_relpath"] = path

    return config


def load_config_cli(config: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    try:
        cfg = load_config(config)
    except FileNotFoundError:
        typer.echo(
            typer.style(
                "ERROR: no configuration file. try:\n$ agolutils config > config.yml",
                fg=typer.colors.RED,
                bold=True,
            )
        )
        raise typer.Exit()

    return cfg
