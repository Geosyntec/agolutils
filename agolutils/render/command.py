from pathlib import Path
from typing import Optional

import typer

from agolutils.config.config import load_config_cli
from agolutils.context.context import load_context_cli

from .render import render_docx_template

app = typer.Typer()


@app.command()
def render_docx(
    context: Path = typer.Option(..., "--context", "--ctx"),
    docx_template: Optional[Path] = typer.Option(None, "--docxtpl"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
):
    """
    >>> agolutils render --config config.yml --context context.json \
        --docxtpl template.docx --output report.docx
    """

    cfg = load_config_cli(config)
    ctx = load_context_cli(context)

    return render_docx_template(ctx, cfg, docx_template, report_file=output)
