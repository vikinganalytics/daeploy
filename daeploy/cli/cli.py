import datetime
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
import json

import click
import pkg_resources
import pytest
import requests
import typer
from cookiecutter.exceptions import FailedHookException, OutputDirExistsException
from cookiecutter.main import cookiecutter
from tabulate import tabulate

from daeploy.cli import cliutils
from daeploy.cli import config
from daeploy.cli.user import app as user_app
import daeploy.communication

THIS_DIR = Path(__file__).parent

DEFAULT_NUMBER_OF_LOGS = "50"

app = typer.Typer()
app.add_typer(user_app, name="user")


def _check_token_validity(host, jwt_token):
    get_ = cliutils.request("GET")
    try:
        get_(
            f"{host}/auth/verify",
            headers={"Authorization": f"Bearer {jwt_token}"},
            allow_redirects=True,
        )
        return True
    except requests.models.HTTPError:
        return False


def _get_services():
    try:
        response = cliutils.get("/services/")
        return response.json()
    except requests.exceptions.MissingSchema:  # If we havent logged in
        return []


def _autocomplete_service_name(incomplete: str):
    services = _get_services()
    valid_completion_items = [service["name"] for service in services]
    for name in valid_completion_items:
        if name.startswith(incomplete):
            yield name


def _autocomplete_service_version(ctx: typer.Context, incomplete: str):
    services = _get_services()
    # Take the service name into consideration to show relevant versions
    name = ctx.params.get("name", "")
    valid_completion_items = [
        service["version"] for service in services if service["name"] == name
    ]
    for ver in valid_completion_items:
        if ver.startswith(incomplete):
            yield ver


def version_callback(value: bool):
    if not value:
        return

    # Get SDK Version
    try:
        sdk_version = pkg_resources.get_distribution("daeploy").version
        typer.echo(f"SDK version: {sdk_version}")
    except pkg_resources.DistributionNotFound:
        pass

    # Get Manager Version
    state = config.CliState()
    if state.active_host():
        try:
            manager_version = requests.get(
                f"{state.active_host()}/~version",
                headers=cliutils.get_request_auth_header(state.active_host_token()),
            )
        except (requests.exceptions.ConnectionError, requests.models.HTTPError):
            typer.echo(
                "Manager version not available."
                " Either the version is < 1.0.0 or it is unreachable."
            )
            raise typer.Exit(0)
        typer.echo(f"Manager version: {manager_version.json()}")

    raise typer.Exit(0)


# pylint: disable=unused-argument
@app.callback()
def _callback(
    context: typer.Context,
    version: bool = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version of the SDK and the Manager",
    ),
):
    """Command-line tool for Daeploy. Initialize a new project,
    deploy services, list them and kill them in a convenient package.

    \f
    Arguments:
        context (Context): Callback context.
        version (bool): If asking for the version of SDK and manager.

    Returns:
        None
    """
    state = config.CliState()
    # Skip host and token checks if --help flag is included.
    if "--help" in click.get_os_args():
        return

    # Skip host and token checks if running login, init or test function.
    if context.invoked_subcommand in ["login", "init", "test"]:
        return

    # Check if the user has an active host
    if state.active_host() is None:
        typer.echo(
            "You must log in to a host with `daeploy login`"
            " before using this function."
        )
        context.abort()

    # Check that the token for the active host is valid
    valid_token = _check_token_validity(state.active_host(), state.active_host_token())
    if not valid_token:
        typer.echo(
            f"You have been logged out from {state.active_host()}."
            " Please log in to the host again."
        )
        context.abort()

    typer.echo(f"Active host: {state.active_host()}")


def deploy_image(name, version, port, source, envvars):
    body = dict(
        name=name,
        version=version,
        port=port,
        image=source,
        run_args={"environment": envvars},
    )
    with cliutils.sigint_ignored():
        cliutils.post(
            "/services/~image",
            json=body,
        )


def deploy_git(name, version, port, source, envvars, build_image):
    body = dict(
        name=name,
        version=version,
        port=port,
        git_url=source,
        run_args={"environment": envvars},
    )
    if build_image:
        body["s2i_build_image"] = build_image

    with cliutils.sigint_ignored():
        cliutils.post(
            "/services/~git",
            json=body,
        )


def deploy_tar(name, version, port, source, envvars, build_image):
    body = dict(
        name=name,
        version=version,
        port=port,
        run_args=json.dumps({"environment": envvars}),  # Form data doesn't support dict
    )
    if build_image:
        body["s2i_build_image"] = build_image

    with cliutils.sigint_ignored():
        cliutils.post(
            "/services/~tar",
            data=body,
            files={
                "file": (
                    "filename",
                    open(str(source), "rb").read(),
                    "application/x-gzip",
                )
            },
        )


def deploy_local_image(name, version, port, source, envvars):
    with cliutils.save_image_tmp(source) as image_path:
        cliutils.post(
            "/services/~upload-image",
            files={
                "image": (
                    image_path.name,
                    open(image_path, "rb").read(),
                    "application/x-gzip",
                )
            },
        )

    deploy_image(name, version, port, source, envvars)


def parse_var(string: str) -> Tuple[str, str]:
    """Parse a key, value pair, separated by '='

    On the command line a declaration will typically look like:
        foo=hello
    or
        foo="hello world"

    Args:
        string (str): Key-value pair separated by '='

    Returns:
        Tuple[str, str]: Parsed key and value
    """
    items = string.split("=")
    key = items[0].strip()  # we remove blanks around keys
    if len(items) > 1:
        # rejoin the rest:
        value = "=".join(items[1:])
    else:
        value = os.environ.get(key, "")  # local envvar or ""
    return (key, value)


def parse_vars(items: List[str]) -> Dict[str, str]:
    """Parse a series of key-value pairs and return a dictionary

    Args:
        items (List[str]): List of key-value pair strings

    Returns:
        Dict[str, str]: Key-value pairs in a dictionary
    """
    keyvalue = {}

    if items:
        for item in items:
            key, value = parse_var(item)
            keyvalue[key] = value
    return keyvalue


@app.command()
def deploy(
    name: str = typer.Argument(
        ...,
        help="Name of the new service.",
        autocompletion=_autocomplete_service_name,
    ),
    version: str = typer.Argument(
        ...,
        help="Version of the new service.",
        autocompletion=_autocomplete_service_version,
    ),
    source: str = typer.Argument(
        ...,
        help=(
            "Path to the source of the service. "
            "Depending on [OPTIONS], (default): [Local directory or tar.gz archive]"
            ", (--image): [name of docker image]"
            ", (--local-image): [name of docker image on your machine]"
            ", (--git): [URL to git repository]"
        ),
    ),
    port: Optional[int] = typer.Option(
        8000, "--port", "-p", help="Internal port for the service."
    ),
    envvars: Optional[List[str]] = typer.Option(
        None,
        "--environment",
        "-e",
        help="Set an environment variable in the service as NAME=VALUE",
    ),
    build_image: Optional[str] = typer.Option(
        None,
        "--build-image",
        help="S2I build image to use when building the service image",
    ),
    image_flag: Optional[bool] = typer.Option(
        False, "--image", "-i", help="Deploy service from an docker image."
    ),
    local_image_flag: Optional[bool] = typer.Option(
        False,
        "--image-local",
        "-I",
        help="Deploy service from a local docker "
        "image (requires docker installation).",
    ),
    git_flag: Optional[bool] = typer.Option(
        False, "--git", "-g", help="Deploy service from a git repository URL."
    ),
):
    """
    Deploy a new service.

    \f
    Args:
        name (str): Name of the new service.
        version (str): Version of the new service.
        source (str): Path to the source of the service.
        port (int, optional): Internal port for the service.
        envvars (List[str], optional): List of environment variable
            key-value strings. Default None
        build_image (str, optional): S2I build image to use when building
            the service image. Default None
        image_flag (bool, optional): Indicate that an image is
            being used for creating the service. Default False.
        local_image_flag (bool, optional): Indicate that a local image
            is being used for creating the service. Default False.
        git_flag (bool, optional): Indicate that a git repository
            is being used for creating the service. Default False.

    Raises:
        Exit: If given an invalid path or user specifies both the -i
            and the -g option.
    """
    cleanup = False

    if sum([image_flag, local_image_flag, git_flag]) > 1:
        typer.echo("Error: You can only select one source flag.")
        raise typer.Exit(1)

    # Parse environment variables
    envvars_dict = parse_vars(envvars or [])

    typer.echo("Deploying service...")
    if image_flag:
        deploy_image(name, version, port, source, envvars_dict)
    elif local_image_flag:
        deploy_local_image(name, version, port, source, envvars_dict)
    elif git_flag:
        deploy_git(name, version, port, source, envvars_dict, build_image)
    # If neither image or git flag is active we default to a tar request.
    else:
        source_path = Path(source).resolve()
        if not source_path.exists():
            typer.echo(f"Could not find anything on the path {str(source_path)}")
            raise typer.Exit(1)

        if source_path.is_dir():
            source_path = cliutils.make_tarball(source_path)
            cleanup = True

        if source_path.suffixes != [".tar", ".gz"]:
            typer.echo(
                "Error: Source must be a .tar.gz file or a "
                "directory when deploying with --tar."
            )
            raise typer.Exit(1)

        deploy_tar(name, version, port, source_path, envvars_dict, build_image)

        if cleanup:
            source_path.unlink()

    typer.echo("Service deployed successfully")
    ls(name, version)  # Show the started service


# pylint: disable=invalid-name
@app.command()
def ls(
    name: Optional[str] = typer.Argument(
        None,
        help="List services with this name.",
        autocompletion=_autocomplete_service_name,
    ),
    version: Optional[str] = typer.Argument(
        None,
        help="List service with this version.",
        autocompletion=_autocomplete_service_version,
    ),
):
    """List running services, filtered by name and version.

    \f
    Args:
        name (str, optional): List services with this name. Defaults to None.
        version (str, optional): List services of a certain name with this
            version. Defaults to None.
    """
    services = _get_services()
    services = cliutils.filter_services_by_name_version(services, name, version)

    # Get the info to print
    keys = ["MAIN", "NAME", "VERSION", "STATUS", "RUNNING"]
    output = []
    for service in services:
        inspection = cliutils.get(
            "/services/~inspection",
            params={"name": service["name"], "version": service["version"]},
        ).json()

        values = cliutils.get_list_values_from_inspection(service, inspection)
        output.append(dict(zip(keys, values)))

    # Fill with empty row to print
    if len(output) == 0:
        output.append(dict(zip(keys, len(keys) * [None])))

    table = tabulate(output, headers="keys")
    typer.echo(f"{table}\n")


@app.command()
def logs(
    name: str = typer.Argument(
        ...,
        help="Name of the service to read logs from",
        autocompletion=_autocomplete_service_name,
    ),
    version: Optional[str] = typer.Argument(
        None,
        help="Version of the service to read logs from."
        " Defaults to the main version of the service",
        autocompletion=_autocomplete_service_version,
    ),
    tail: Optional[str] = typer.Option(
        DEFAULT_NUMBER_OF_LOGS,
        "--tail",
        "-n",
        help="Output specified number of lines at the end of logs."
        'Use "all" to get all logs.',
    ),
    follow: Optional[bool] = typer.Option(
        False, "--follow", "-f", help="If the logs should be followed"
    ),
    date: Optional[datetime.datetime] = typer.Option(
        None,
        "--date",
        "-d",
        help="Show logs since given datetime.",
    ),
):
    """Shows the logs for a service.

    \f
    Args:
        name (str): Name of the service. Defaults to None.
        version (str, optional): Version of the service. Defaults to None.
        tail (int, optional): Output specified number of lines at the end of logs.
            Default to 50
        follow (bool, optional): If the logs should be followed. Defaults to False.
        date (datetime, optional): Show logs since given datetime.
            Valid forrmats: [%Y-%m-%d|%Y-%m-%dT%H:%M:%S|%Y-%m-%d %H:%M:%S].
            Default to None.

    Raises:
        Exit: If the tail input has a wrong type.
    """

    # Check if service exists
    services = _get_services()
    services = cliutils.filter_services_by_name_version(services, name, version)
    cliutils.check_matching_services(services)

    # Check correct type for tail
    if tail == "all":
        tail = None
    else:
        try:
            tail = int(tail)
        except ValueError:
            typer.echo('Wrong input type for tail, needs to be an integer or "all"')
            raise typer.Exit(1)

    # If no version is specified, read logs from main version.
    if not version:
        service = cliutils.filter_services(services, True, "main")
        version = service[0]["version"]

    # Get the logs
    response = cliutils.get(
        "/services/~logs/",
        params={
            "name": name,
            "version": version,
            "tail": tail,
            "follow": follow,
            "since": date,
        },
        stream=True,
    )
    for log_line in response.iter_lines():
        if log_line:
            decoded_line = log_line.decode("utf-8")
            typer.echo(decoded_line)


@app.command()
def kill(
    name: Optional[str] = typer.Argument(
        None,
        help="Name of the service(s) to kill.",
        autocompletion=_autocomplete_service_name,
    ),
    version: Optional[str] = typer.Argument(
        None,
        help="Version of the service to kill.",
        autocompletion=_autocomplete_service_version,
    ),
    all_: Optional[bool] = typer.Option(False, "--all", "-a", help="Kill all services"),
    validation: Optional[bool] = typer.Option(
        False,
        "--yes",
        help="Give confirmation to kill services." " Skips prompt, use with caution.",
    ),
    keep_image: Optional[bool] = typer.Option(
        False,
        "-i",
        "--keep-image",
        help="Keep the image(s) of the killed service(s). "
        "Might result in dangling images.",
    ),
):
    """Kill one or multiple services by name and version.

    \f
    Args:
        name (str, optional): Name of the service(s) to kill. Defaults to None.
        version (str, optional): Version of the service to kill. Defaults to None.
        all_ (bool, optional): Kill all services. Defaults to False.
        validation (bool, optional): Give confirmation to kill services at runtime.
            Skips prompt, use with caution. Defaults to False.
        keep_image (bool, optional): Keep the image(s) of the killed service(s).

    Raises:
        Exit: If there are no services to kill matching the given description.
    """
    services = _get_services()

    if not all_ and not name and not version:
        ls(name, version)  # List all services
        typer.echo(
            "Include the name or name and version of the service(s)"
            " to kill or -a/--all to kill all."
        )
        raise typer.Exit(1)

    services = cliutils.filter_services_by_name_version(services, name, version)
    cliutils.check_matching_services(services)

    ls(name, version)  # List the services matching name and version

    # Get user validation
    validation = validation or typer.confirm(
        "Are you sure you want to kill the above service(s)?"
    )
    if not validation:
        typer.echo("Service(s) not killed")
        raise typer.Exit(0)

    for service in cliutils.sort_main_service_last(services):
        cliutils.delete(
            "/services/",
            json={"name": service["name"], "version": service["version"]},
            params={"remove_image": not keep_image},
        )
        typer.echo(f"Service {service['name']} {service['version']} killed.")


@app.command()
def assign(
    name: str = typer.Argument(
        ...,
        help="Name of version to change main",
        autocompletion=_autocomplete_service_name,
    ),
    version: str = typer.Argument(
        ...,
        help="Version of service to set as main",
        autocompletion=_autocomplete_service_version,
    ),
    validation: Optional[bool] = typer.Option(
        False,
        "--yes",
        help="Give confirmation to assign service." " Skips prompt, use with caution.",
    ),
):
    """Change main version of a service.

    \f
    Args:
        name (str): Name of the service to change to primary.
        version (str): Version of the service to change to primary.
        validation (bool, optional): Give confirmation to assign service.
            Skips prompt, use with caution.

    Raises:
        Exit: If the user does not validate the assign.
    """
    validation = validation or typer.confirm(
        f"Change {name} {version} to main?", default=False
    )
    if not validation:
        typer.echo("Assign cancelled.")
        raise typer.Exit()

    cliutils.put(
        "/services/~assign",
        json={"name": name, "version": version},
    )
    typer.echo(f"Changed main version to {name} {version}")
    ls(name=name, version=None)


@app.command()
def init(
    path: Optional[Path] = typer.Argument(
        Path.cwd(), help="Project generation output directory."
    ),
    project_name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Name of the project to skip prompt."
    ),
):
    """Generates skeleton code for a new Daeploy project.

    \f
    Args:
        path (Path, optional): Project generation output directory.
        project_name (str, optional): Name of the project to skip prompt.

    Raises:
        Exit: If the output directory could not be found
    """
    path = path.resolve()

    if not path.is_dir():
        typer.echo(f"Could not find the directory: {str(path)}")
        raise typer.Exit(1)
    # Find out which daeploy version that should be used by the service
    try:
        dist = pkg_resources.get_distribution("daeploy")
        daeploy_specifier = (
            str(dist.as_requirement())
            if dist.version != "0.0.0.dev0"
            else dist.project_name
        )  # Use full specificer unless in dev environment, then just go for the latest
    except pkg_resources.DistributionNotFound:
        typer.echo(
            "`daeploy` package not found, assuming latest version "
            "should be used for the generated project."
        )
        daeploy_specifier = "daeploy"

    try:
        extra_content = {"_daeploy_specifier": daeploy_specifier}
        if project_name:
            extra_content["project_name"] = project_name

        cookiecutter(
            str(THIS_DIR / "service_template"),
            output_dir=str(path),
            extra_context=extra_content,
            no_input=bool(project_name),
        )
    except FailedHookException:
        pass
    except OutputDirExistsException as exc:
        typer.echo(f"{str(exc)}. Could not create a new project.")


@app.command()
def token(
    lifetime: Optional[int] = typer.Argument(
        None,
        help=(
            "Number of days the token should be valid."
            " If not specified, the token will never expire."
        ),
    )
):
    """Generate a new authentication token.

    \f
    Args:
        lifetime (Optional[int], optional): Number of days the token should be valid.
            Default to None which correpsonds to a long-lived token.
    """
    response = cliutils.post(
        "/auth/token",
        json={"expire_in_days": lifetime},
    )
    token_value = response.json()["Token"]
    typer.echo(
        'Use the token in the header {"Authorization": "Bearer token"},'
        " for further details see the docs"
    )
    typer.echo(token_value)


@app.command()
def login(
    host: Optional[str] = typer.Option(
        None, "--host", "-h", help="Host address to log in to."
    ),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username"),
    password: Optional[str] = typer.Option(
        None,
        "--password",
        "-p",
        help="Password. Use with caution because input"
        " will be saved in terminal history.",
    ),
    _token: Optional[str] = typer.Option(
        None,
        "--token",
        "-t",
        help="Log in to a manager using a token instead of username and password.",
    ),
):
    """Log in to the specified host.

    \f
    Args:
        host (str, optional): Host address to log in to. Defaults to None
            in which case you will be prompted.
        username (str, optional): Username. Defaults to None in
            which case you will be prompted.
        password (str, optional): Password. Use with caution because input
            will be saved in terminal history. Defaults to None in
            which case you will be prompted.
        _token (str, optional): Log in to a manager using a token instead
            of username and password. Defaults to None.

    Raises:
        Exit: If given invalid login credentials or host
    """
    state = config.CliState()
    # Print any existing hosts and let the user choose with a number
    current_hosts = state.list_hosts()
    if len(current_hosts) > 0 and not host:
        typer.echo("Current hosts:")
        for i, key in enumerate(current_hosts):
            typer.echo(f"{i} - {key}")

    # Select host
    host = host or typer.prompt("Enter Daeploy host")

    # If user chooses a number from the current hosts
    if host.isdigit():
        try:
            host = list(current_hosts)[int(host)]
        except IndexError:
            typer.echo(f"Index {host} out of range")
            raise typer.Exit(1)

    # Make sure protocol is present
    if not host.startswith(("http://", "https://")):
        typer.echo("Host URL must start with http:// or https://")
        raise typer.Exit(1)

    # Ensure we dont have a trailing slash
    host = host.rstrip("/")

    access_token = _token or state.host_token(host)

    # If the user already has a valid token we just change the active host
    if _check_token_validity(host, access_token):
        state.add_host(host, access_token)
        state.activate_host(host)
        typer.echo(f"Changed host to {state.active_host()}")
        raise typer.Exit(0)

    # If the token argument was given with an invalid token
    if _token:
        typer.echo("Invalid token given")
        raise typer.Exit(1)

    typer.echo(f"Logging in to Daeploy instance at {host}")
    username = username or typer.prompt("Username", type=str)
    password = password or typer.prompt("Password", type=str, hide_input=True)

    # A session scope is needed in order to keep the cookies alive
    with daeploy.communication.DaeploySession(log_func=typer.echo) as session:
        session_post = cliutils.request_error_handling(
            cliutils.check_connection(session.post)
        )

        # Login using provided credentials
        session_post(
            f"{host}/auth/login",
            data={"username": username, "password": password},
        )

        # Verify that we have received a cookie with a token
        access_token = session.cookies.get("daeploy")
        if not access_token:
            typer.echo("Login failed!")
            raise typer.Exit(1)

        # Save the retreived token for future usage
        state.add_host(host, access_token)
        state.activate_host(host)
        typer.echo(f"Changed host to {state.active_host()}")


@app.command()
def test(
    service_path: Optional[Path] = typer.Argument(
        Path.cwd(), help="Path to the directory of the service to test"
    )
):
    """Test a service before deployment.

    \f
    Args:
        service_path (Path, optional): Path to the directory of the service
            to test. Defaults to Path.cwd().

    Raises:
        Exit: Exits with exit code 0 if all tests pass, otherwise 1-5
    """
    sys.path.append(str(service_path))
    exit_code = pytest.main([str(service_path)])
    raise typer.Exit(exit_code)


@app.command(help="Log out from a host")
def logout(
    host: Optional[str] = typer.Argument(
        None,
        help="Host to log out from and remove token. "
        "Logs out from the active host unless specified",
    )
):
    state = config.CliState()

    logout_host = host or state.active_host()
    try:
        state.logout(logout_host)
    except KeyError:
        typer.echo(f"Not logged in to {logout_host}")
        raise typer.Exit(1)

    typer.echo(f"Logged out from {logout_host}")


# Expose click object for automated documentation with sphinx-click
typer_click_object = typer.main.get_command(app)
