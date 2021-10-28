"""Subcommand for user management"""

import typer

from daeploy.cli import cliutils


app = typer.Typer(help="Collection of user management commands")
typer.Option(None, "-p", "--password", expose_value=False)


@app.command()
def create(
    username: str = typer.Argument(..., help="Username of new user"),
    password: str = typer.Option(
        None,
        "-p",
        "--password",
        prompt=True,
        confirmation_prompt=True,
        hide_input=True,
        help="Give password in command instead of in prompt. Warning: Insecure",
    ),
):
    cliutils.post(
        "/"
    )