"""Subcommand for user management"""

import typer
from tabulate import tabulate

from daeploy.cli import cliutils


app = typer.Typer(help="Collection of user management commands")
typer.Option(None, "-p", "--password", expose_value=False)


@app.command("add", help="Add a new user to the active host")
def add_user(
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
    cliutils.post(f"/admin/user/{username}", json={"password": password})
    typer.echo(f"Added user '{username}'")


@app.command("rm", help="Delete a user from the active host")
def delete_user(
    username: str = typer.Argument(..., help="Username of user to delete"),
    validation: bool = typer.Option(
        False,
        "--yes",
        help="Give confirmation to delete user. Skips prompt, use with caution.",
    ),
):
    validation = validation or typer.confirm(
        f"Are you sure you want to remove user '{username}'?"
    )
    if not validation:
        typer.echo(f"User '{username}' not deleted")
        raise typer.Exit(0)

    cliutils.delete(f"/admin/user/{username}")
    typer.echo(f"User '{username}' deleted")


@app.command("ls", help="List all users for the active host")
def list_users():
    users = cliutils.get("/admin/user/").json()
    table = tabulate([[user] for user in users], headers=["users"])
    typer.echo(f"{table}\n")


@app.command("update", help="Change the password of a user on the active host")
def change_password(
    username: str = typer.Argument(..., help="Username of user to change password for"),
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
    cliutils.put(f"/admin/user/{username}", json={"password": password})
    typer.echo(f"Changed password of user '{username}'")
