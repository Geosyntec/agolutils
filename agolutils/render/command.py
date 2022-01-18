from typing import Optional
from pathlib import Path

import typer

from agolutils.config.config import load_config_cli
from agolutils.context.context import load_context_cli
from .render import render_docx_template

app = typer.Typer()


@app.command()
def render(
    context: Path = typer.Option(..., "--context", "--ctx"),
    output: Path = typer.Option(
        ...,
        "--output",
        "-o",
    ),
    docx_template: Optional[Path] = typer.Option(None, "--docxtpl"),
    template: Optional[Path] = typer.Option(None, "--tpl"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """
    >>> agolutils render --config config.yml --context context.json --docxtpl template.docx --output report.docx
    """

    if not (docx_template or template):
        typer.echo("one of --docxtpl or --tpl are required")
        raise typer.Exit()

    cfg = load_config_cli(config)
    ctx = load_context_cli(context)

    if docx_template:
        return render_docx_template(cfg, ctx, docx_template, output)

    typer.echo("--tpl is not yet supported")
    raise typer.Exit()
