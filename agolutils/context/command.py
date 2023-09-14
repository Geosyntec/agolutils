import json
from pathlib import Path
from typing import List, Optional

import typer

from agolutils.config.config import load_config_cli
from agolutils.io import load_json
from agolutils.utils import collect_files, make_path


app = typer.Typer()


@app.command()
def combine(
    filepaths: List[Path] = typer.Argument(
        ...,
        help="pass files ",
        exists=True,
        file_okay=True,
        dir_okay=True,
        allow_dash=True,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
    ),
):
    files = collect_files(filepaths)

    ctx = {}

    for file in files:
        new_ctx = load_json(file)
        ctx.update(new_ctx)

    content = json.dumps(ctx, indent=2)
    if output:
        output = make_path(output)
        output.write_text(content)
    else:
        typer.echo(content)
    return ctx


@app.command()
def fetch_survey123(
    oids: List[str] = typer.Argument(...),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    env: Optional[Path] = typer.Option(".env", "--env"),
):
    from agolutils.arcgis.survey123 import build_survey123_contexts

    cfg = load_config_cli(config)
    files = build_survey123_contexts(cfg, oids, env=env)

    return files
