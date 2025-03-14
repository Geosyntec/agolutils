from typing import List

import typer

from agolutils import config, context, render
from agolutils.utils import search_files

app = typer.Typer()
app.add_typer(context.app, name="context")
app.registered_commands += (
    render.app.registered_commands + config.app.registered_commands
)


@app.command()
def search(patterns: List[str] = typer.Argument(..., help="glob files ")):
    files = search_files(patterns)
    str_files = "\n".join(map(str, files))
    if files:
        typer.echo(str_files)
    else:
        typer.echo("None found.")

    return files


if __name__ == "__main__":
    app()
