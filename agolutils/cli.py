from typing import List

import typer

from agolutils import render, context, config
from agolutils.utils import search_files


app = typer.Typer()
app.add_typer(context.app, name="context")
app.registered_commands += (
    render.app.registered_commands + config.app.registered_commands
)


@app.command()
def search(
    patterns: List[str] = typer.Argument(
        ...,
        help="glob files ",
    ),
):
    files = search_files(patterns)
    typer.echo(f"found: {files}")

    return files


if __name__ == "__main__":
    app()
