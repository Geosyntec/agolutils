import typer

from .config import config_file

app = typer.Typer()


@app.command()
def config():
    """Print the starter config to stdout.

    $ agolutils config > config.yml
    """
    typer.echo(config_file)
    return
