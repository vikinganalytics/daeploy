import os
from pathlib import Path
import time
import tarfile
import subprocess
from unittest.mock import MagicMock, patch
from random import choice
from string import ascii_uppercase

import pytest
import docker
import docker.errors
import threading
from typer.testing import CliRunner

from daeploy.cli.cliutils import (
    filter_services_by_name_version,
    sort_main_service_last,
    make_tarball,
    save_image_tmp,
)
from daeploy.cli.cli import app, _get_services_for_autocompletion, parse_var, parse_vars
import daeploy.cli.cli as cli
import daeploy.cli.config as config
from manager.runtime_connectors import create_container_name
from manager.routers.auth_api import new_api_token, verify_request
from manager.database.database import remove_db

from manager.constants import (
    DAEPLOY_CONTAINER_TYPE_KEY,
    DAEPLOY_CONTAINER_TYPE_SERVICE,
    DAEPLOY_SERVICE_AUTH_TOKEN_KEY,
)

THIS_DIR = Path(__file__).parent
TMP_PROJECT_NAME = "tmp_proj"
TAR_FILE_NAME = "test_tar.tar.gz"
PYTHON_FILE_NAME = "main.py"
MAX_FILE_SIZE = int(1e6)  # 1 MB

runner = CliRunner()


@pytest.fixture
def tar_file(tmp_path):
    with tarfile.open(tmp_path / TAR_FILE_NAME, "w:gz") as tar:
        p = tmp_path / PYTHON_FILE_NAME
        p.write_text("Hallaballo!")
        tar.add(p)
        tar.close()
    yield str(tmp_path / TAR_FILE_NAME)


@pytest.fixture
def too_big_tar_file(tmp_path):
    with tarfile.open(tmp_path / TAR_FILE_NAME, "w:gz") as tar:
        p = tmp_path / PYTHON_FILE_NAME
        p.write_text(
            "".join(
                choice(ascii_uppercase) for i in range(2 * MAX_FILE_SIZE)
            )  # Random string of length 2*MAX_FILE_SIZE
        )
        tar.add(p)
        tar.close()
    yield str(tmp_path / TAR_FILE_NAME)


@pytest.fixture
def dummy_service():
    service_name = "test_service"
    version = "1.0.0"
    container_name = create_container_name(service_name, version)
    client = docker.from_env()
    token = new_api_token()

    container = client.containers.run(
        "traefik/whoami:latest",
        name=container_name,
        detach=True,
        labels={
            DAEPLOY_CONTAINER_TYPE_KEY: DAEPLOY_CONTAINER_TYPE_SERVICE,
        },
        environment={
            DAEPLOY_SERVICE_AUTH_TOKEN_KEY: token["Token"],
        },
        ports={80: 6000},
        auto_remove=True,
    )
    try:
        yield container
    finally:
        container.remove(force=True)


@pytest.fixture
def clean_services():
    try:
        yield
    finally:
        runner.invoke(app, ["kill", "-a", "--yes"])


@pytest.fixture
def cli_auth():
    config.initialize_cli_configuration()
    try:
        yield
    finally:
        config.CONFIG_FILE.unlink()


@pytest.fixture()
def cli_auth_login(dummy_manager, cli_auth):
    runner.invoke(app, ["login"], input="http://localhost:5080\nadmin\nadmin\n")
    yield


@pytest.fixture(scope="module")
def dummy_manager():
    my_env = os.environ.copy()
    my_env["DAEPLOY_AUTH_ENABLED"] = "true"
    try:
        p = subprocess.Popen(
            ["uvicorn", "manager.app:app"],
            # For some reason, the tar related tests cannot finish if we use PIPE here.
            # This was first noticed when added logging, PR 223.
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            env=my_env,
        )
        time.sleep(5)
        yield

    finally:
        p.terminate()
        remove_db()


# The same test but with a manager can be found in the e2e tests.
def test_version_flag_without_manager():
    result = runner.invoke(
        app,
        ["--version"],
    )
    assert result.exit_code == 0
    assert "Manager" not in result.stdout


def test_deploy_from_git_source(dummy_manager, cli_auth_login, clean_services):
    # Start a container
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.1",
            "--git",
            "https://github.com/sclorg/django-ex",
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout


def test_deploy_from_image_source(dummy_manager, cli_auth_login, clean_services):
    # Start a container

    result = runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "0.1.2",
            "traefik/whoami:latest",
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout


def test_deploy_from_image_source(dummy_manager, cli_auth_login, clean_services):
    # Start a container

    # Successful
    result = runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "0.1.2",
            "traefik/whoami:latest",
            "-e",
            "TESTVAR1=TESTVAL1",
            "-e",
            "TESTVAR2=TESTVAL2",
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout


def test_deploy_from_tar_source(
    dummy_manager, cli_auth_login, tar_file, clean_services
):
    # Start a container

    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            tar_file,
        ],
    )
    assert Path(tar_file).exists()
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout


def test_deploy_from_tar_source_build_image(
    dummy_manager, cli_auth_login, tar_file, clean_services
):
    # Start a container

    # Successful
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.2.0",
            tar_file,
            "--build-image",
            "centos/python-38-centos7",
        ],
    )
    assert Path(tar_file).exists()
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout

    # nonexisting build image
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            tar_file,
            "--build-image",
            "builderimagethatdoesnotexist",
        ],
    )
    assert Path(tar_file).exists()
    assert result.exit_code == 1
    assert "ERROR" in result.stdout


def test_deploy_from_tar_wrong_path(dummy_manager):
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            "./thispathdoesnotexist",
        ],
    )
    assert result.exit_code == 1


def test_deploy_tar_from_dir(dummy_manager, cli_auth_login, tmp_path, clean_services):
    project_path = tmp_path / "testdir"
    project_path.mkdir()

    with (project_path / "foo.txt").open("w") as file_handle:
        file_handle.write("Boooo!")

    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            str(project_path),
        ],
    )
    # Make sure that the tar.gz is removed
    assert not project_path.with_suffix(".tar.gz").exists()
    assert result.exit_code == 0


def test_make_tarball(tmp_path):
    project_path = tmp_path / "testdir"
    project_path.mkdir()

    with (project_path / "foo.txt").open("w") as file_handle:
        file_handle.write("Boooo!")

    make_tarball(project_path)
    # Make sure that the tar.gz is created.
    assert project_path.with_suffix(".tar.gz").is_file()
    # Make sure that the root of the the tar is the same as the folder.
    tar_file_names = []
    with tarfile.open(project_path.with_suffix(".tar.gz"), "r") as f:
        tar_file_names = f.getnames()
    assert "foo.txt" in tar_file_names
    assert "/testdir/foo.txt" not in tar_file_names


def test_deploy_tar_from_current_dir(
    dummy_manager, tmp_path, cli_auth_login, clean_services
):
    with Path(tmp_path, "foo.txt").open("w") as file_handle:
        file_handle.write("Boooo!")

    original_wd = os.getcwd()
    os.chdir(tmp_path)
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            ".",
        ],
    )
    os.chdir(original_wd)
    assert result.exit_code == 0


@pytest.fixture
def test_image():
    image_tag = "traefik/whoami:latest"
    client = docker.from_env()
    client.images.pull(image_tag)
    yield image_tag


def test_save_image_tmp(test_image):
    with save_image_tmp(test_image) as image_path:
        assert image_path.exists()
    assert not image_path.exists()


def test_deploy_local_image(
    dummy_manager, tmp_path, cli_auth_login, clean_services, test_image
):
    result = runner.invoke(app, ["deploy", "local_image", "1.0.0", "-I", test_image])
    assert result.exit_code == 0
    assert not Path("tmpimage.tar").exists()


def test_deploy_local_image_not_found(dummy_manager, cli_auth_login, clean_services):
    result = runner.invoke(app, ["deploy", "local_image", "1.0.0", "-I", "notanimage"])
    assert result.exit_code == 1


def test_deploy_local_image_no_docker(dummy_manager, cli_auth_login, clean_services):
    with patch(
        "daeploy.cli.cliutils.docker.from_env",
        side_effect=docker.errors.DockerException("No docker"),
    ):
        result = runner.invoke(
            app, ["deploy", "local_image", "1.0.0", "-I", "notanimage"]
        )
    assert result.exit_code == 1
    assert "Error connecting to docker" in result.stdout


def test_deploy_two_flags_error(dummy_manager, cli_auth_login, tar_file):
    result = runner.invoke(
        app,
        [
            "deploy",
            "--git",
            "--image",
            "test_service",
            "0.1.0",
            tar_file,
        ],
    )
    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_deploy_and_kill(dummy_manager, cli_auth_login, clean_services):
    # Start a container
    result = runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.2.3",
            "traefik/whoami:latest",
            "--port",
            "1337",
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout

    client = docker.from_env()
    container = client.containers.get(create_container_name("test_service", "1.2.3"))
    port = list(container.ports.keys())[0].split("/")[0]
    assert port == "1337"

    # List it
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert "NAME" in result.stdout
    assert "test_service  1.2.3" in result.stdout

    # Don't kill it
    result = runner.invoke(app, ["kill", "test_service", "1.2.3"], input="n")
    assert result.exit_code == 0
    assert "Service(s) not killed" in result.stdout

    # Kill it
    result = runner.invoke(app, ["kill", "test_service", "1.2.3"], input="y")
    assert result.exit_code == 0
    assert "Service test_service 1.2.3 killed." in result.stdout


def test_kill_keep_image(dummy_manager, cli_auth_login, clean_services):
    result = runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.2.3",
            "traefik/whoami:latest",
        ],
    )

    result = runner.invoke(app, ["kill", "-i", "test_service", "1.2.3", "--yes"])
    assert result.exit_code == 0

    client = docker.from_env()
    client.images.get("traefik/whoami:latest")
    with pytest.raises(docker.errors.NotFound):
        client.containers.get(create_container_name("test_service", "1.2.3"))


def test_ls_without_services(dummy_manager, cli_auth_login):
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert "NAME" in result.stdout


def test_ls_with_database_desync(dummy_manager, dummy_service, cli_auth_login):
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 1
    assert "Command failed: 412" in result.stdout


def test_assign(dummy_manager, cli_auth_login, tar_file, clean_services):
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            tar_file,
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout

    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.2.0",
            tar_file,
        ],
    )
    assert result.exit_code == 0
    assert "Service deployed successfully" in result.stdout

    # With prompt
    result = runner.invoke(app, ["assign", "test_service", "0.2.0"], input="y")
    assert result.exit_code == 0
    assert "Changed main version to test_service 0.2.0" in result.stdout

    # Without prompt
    result = runner.invoke(app, ["assign", "test_service", "0.1.0", "--yes"])
    assert result.exit_code == 0
    assert "Changed main version to test_service 0.1.0" in result.stdout


def test_init_not_logged_in(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)], input="test_project")
    assert result.exit_code == 0
    assert (tmp_path / "test_project").is_dir()


def test_init(dummy_manager, tmp_path, cli_auth_login, clean_services):
    result = runner.invoke(app, ["init", str(tmp_path)], input="test_project")

    assert result.exit_code == 0
    assert (tmp_path / "test_project").is_dir()
    assert (tmp_path / "test_project" / "requirements.txt").read_text() == "daeploy"


def test_init_no_prompt(dummy_manager, tmp_path, cli_auth_login, clean_services):
    result = runner.invoke(app, ["init", str(tmp_path), "-n", "test_project"])

    assert result.exit_code == 0
    assert (tmp_path / "test_project").is_dir()
    assert (tmp_path / "test_project" / "requirements.txt").read_text() == "daeploy"


def test_filter_services_by_name_version():
    services = [
        {"name": "1", "version": "1.0.0", "etc": "more_info"},
        {"name": "1", "version": "3.1.0", "etc": "more_info"},
        {"name": "2", "version": "1.0.1", "etc": "more_info"},
        {"name": "2", "version": "3.1.0", "etc": "more_info"},
        {"name": "3", "version": "1.0.0", "etc": "more_info"},
        {"name": "1", "version": "1.1.0", "etc": "more_info"},
    ]

    result = filter_services_by_name_version(services, None, None)
    assert result == services

    result = filter_services_by_name_version(services, "1", None)
    assert result == [services[0], services[1], services[5]]

    result = filter_services_by_name_version(services, None, "1.0.0")
    assert result == [services[0], services[4]]

    result = filter_services_by_name_version(services, "1", "1.0.0")
    assert result == [services[0]]


def test_sort_main_last():
    services = [
        {"name": "1", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "1", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "2", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "3", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "1", "version": "1.1.0", "etc": "more_info", "main": False},
        {"name": "2", "version": "1.0.1", "etc": "more_info", "main": True},
    ]
    sorted_services = sort_main_service_last(services)
    assert sorted_services == [
        {"name": "1", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "2", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "1", "version": "1.1.0", "etc": "more_info", "main": False},
        {"name": "1", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "3", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "2", "version": "1.0.1", "etc": "more_info", "main": True},
    ]


def test_login_success(dummy_manager, cli_auth):
    result = runner.invoke(
        app, ["login"], input="http://localhost:5080\nadmin\nadmin\n"
    )

    assert result.exit_code == 0


def test_login_success_args_host(dummy_manager, cli_auth):
    result = runner.invoke(
        app, ["login", "--host", "http://localhost:5080"], input="admin\nadmin\n"
    )

    assert result.exit_code == 0


def test_login_success_args_host_username(dummy_manager, cli_auth):
    result = runner.invoke(
        app,
        ["login", "--host", "http://localhost:5080", "--username", "admin"],
        input="admin\n",
    )

    assert result.exit_code == 0


def test_login_success_args_host_username_password(dummy_manager, cli_auth):
    result = runner.invoke(
        app,
        [
            "login",
            "--host",
            "http://localhost:5080",
            "--username",
            "admin",
            "--password",
            "admin",
        ],
    )

    assert result.exit_code == 0


def test_login_failure(dummy_manager, cli_auth):
    result = runner.invoke(
        app, ["login"], input="http://localhost:5080\nadmin\nwrongpassword\n"
    )

    assert result.exit_code == 1


def test_login_wrong_host(dummy_manager, cli_auth):
    result = runner.invoke(
        app, ["login"], input="http://foreignhost:5080\nadmin\nadmin\n"
    )
    assert result.exit_code == 1

    result = runner.invoke(app, ["login"], input="asdfgh\nadmin\nadmin\n")
    assert result.exit_code == 1
    assert "Host URL must start with http:// or https://" in result.stdout


def test_login_two_hosts(dummy_manager, cli_auth_login):
    result = runner.invoke(
        app, ["login"], input="http://localhost:8000\nadmin\nadmin\n"
    )
    assert result.exit_code == 0
    assert "Changed host to http://localhost:8000" in result.stdout

    # Change back with number
    result = runner.invoke(app, ["login"], input="0\n")
    assert result.exit_code == 0
    assert "Changed host to http://localhost:5080" in result.stdout


def test_login_token(dummy_manager, cli_auth_login):
    result = runner.invoke(
        app,
        ["token", "10"],
    )
    assert result.exit_code == 0
    token = result.stdout.splitlines()[2]

    result = runner.invoke(
        app, ["login", "--host", "http://localhost:5080", "--token", token]
    )
    assert result.exit_code == 0
    assert "Changed host to http://localhost:5080" in result.stdout

    # Check that token is valid
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0


def test_invalid_access_token(dummy_manager, cli_auth_login):
    # Change the access token
    configuration = config.read_cli_configuration()
    configuration["access_tokens"][configuration["active_host"]] = ""
    config.save_cli_configuration(configuration)

    # Test that it is invalid
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 1
    assert "You have been logged out from" in result.stdout

    result = runner.invoke(app, ["login"], input="0\nadmin\nadmin\n")
    assert result.exit_code == 0
    assert "Changed host to http://localhost:5080" in result.stdout

    # Test that it works again
    result = runner.invoke(app, ["ls"])
    assert result.exit_code == 0
    assert "NAME" in result.stdout


def test_change_host_number_out_of_range(dummy_manager, cli_auth_login):
    result = runner.invoke(app, ["login"], input="100\n")
    assert "Index 100 out of range" in result.stdout


def test_autocompletion_name():
    services = [
        {"name": "myservice", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "myservice", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "theirservice", "version": "2.1.0", "etc": "more_info", "main": True},
    ]
    cli._get_services_for_autocompletion = MagicMock(return_value=services)
    for name in cli._autocomplete_service_name("my"):
        assert name == "myservice"

    for name in cli._autocomplete_service_name("their"):
        assert name == "theirservice"


def test_autocompletion_version():
    services = [
        {"name": "myservice", "version": "1.0.0", "etc": "more_info", "main": True},
        {"name": "myservice", "version": "3.1.0", "etc": "more_info", "main": False},
        {"name": "theirservice", "version": "2.1.0", "etc": "more_info", "main": True},
    ]
    cli._get_services_for_autocompletion = MagicMock(return_value=services)

    class Context:
        def __init__(self, name):
            self.params = {"name": name}

    ctx = Context("myservice")
    for name in cli._autocomplete_service_version(ctx, "1."):
        assert name == "1.0.0"

    for name in cli._autocomplete_service_version(ctx, "3."):
        assert name == "3.1.0"

    ctx = Context("theirservice")
    for name in cli._autocomplete_service_version(ctx, "2."):
        assert name == "2.1.0"


def test_get_services_for_autocompletion(cli_auth_login, tar_file, clean_services):
    result = runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.1.0",
            tar_file,
        ],
    )
    assert result.exit_code == 0

    services = _get_services_for_autocompletion()
    assert len(services) == 1
    assert services[0]["name"] == "test_service"


def test_get_services_for_autocompletion_no_connection():
    services = _get_services_for_autocompletion()
    assert services == []


def test_logs_name_and_version_specified(cli_auth_login, clean_services):
    runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.0.0",
            "traefik/whoami:latest",
        ],
    )
    result_logs = runner.invoke(
        app,
        [
            "logs",
            "test_service",
            "1.0.0",
        ],
    )

    assert result_logs.exit_code == 0
    assert "Starting up on port 80" in result_logs.stdout


def test_logs_tail(cli_auth_login, clean_services):
    runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.0.0",
            "hello-world",
        ],
    )
    all_logs = runner.invoke(
        app,
        [
            "logs",
            "test_service",
            "1.0.0",
        ],
    )

    tailed_logs = runner.invoke(
        app,
        ["logs", "test_service", "1.0.0", "--tail", "2"],
    )
    assert all_logs.exit_code == 0
    assert tailed_logs.exit_code == 0
    # Last log
    assert "https://docs.docker.com/get-started/" in all_logs.stdout
    assert "https://docs.docker.com/get-started/" in tailed_logs.stdout
    # Fist log
    assert "Hello from Docker!" in all_logs.stdout
    assert "Hello from Docker!" not in tailed_logs.stdout


def test_logs_date_format(cli_auth_login, clean_services):
    runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.0.0",
            "hello-world",
        ],
    )
    logs = runner.invoke(
        app,
        ["logs", "test_service", "1.0.0", "--date", "2020/01/24"],
    )
    assert logs.exit_code == 2
    assert "invalid datetime format" in logs.stdout
    logs = runner.invoke(
        app,
        ["logs", "test_service", "1.0.0", "--date", "1970-01-24"],
    )
    assert logs.exit_code == 0
    assert "Hello from Docker!" in logs.stdout


def test_logs_stream(cli_auth_login):
    def kill_service():
        time.sleep(10)
        runner.invoke(app, ["kill", "test_service"], input="y")

    runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "1.0.0",
            "chentex/random-logger",
        ],
    )
    first_logs = runner.invoke(
        app,
        [
            "logs",
            "test_service",
            "1.0.0",
        ],
    )

    threading.Thread(target=kill_service).start()
    streamed_logs = runner.invoke(
        app,
        ["logs", "test_service", "1.0.0", "--follow"],
    )
    assert len(streamed_logs.stdout) > len(first_logs.stdout)


def test_logs_no_name_and_no_version_specified_error(cli_auth_login):
    result_logs = runner.invoke(
        app,
        [
            "logs",
        ],
    )

    assert result_logs.exit_code == 2


def test_logs_wrong_service_name(cli_auth_login):
    result_logs = runner.invoke(
        app,
        ["logs", "mv"],
    )

    assert result_logs.exit_code == 1
    assert "No services match the given name and version" in result_logs.stdout


def test_logs_main_version_if_no_version_specified(
    cli_auth_login, tar_file, clean_services
):
    runner.invoke(
        app,
        [
            "deploy",
            "--image",
            "test_service",
            "0.0.1",
            "traefik/whoami:latest",
        ],
    )
    runner.invoke(
        app,
        [
            "deploy",
            "test_service",
            "0.0.2",
            tar_file,
        ],
    )
    result_logs = runner.invoke(app, ["logs", "test_service"])

    assert result_logs.exit_code == 0
    assert "Starting up on port 80" in result_logs.stdout

    # Switch main version
    runner.invoke(app, ["assign", "test_service", "0.0.2"], input="y")
    result_logs2 = runner.invoke(app, ["logs", "test_service"])
    assert result_logs.exit_code == 0
    assert result_logs2 != result_logs


def test_generate_token_not_logged_in_failed():
    result = runner.invoke(
        app,
        [
            "token",
        ],
    )
    assert result.exit_code == 1


def test_generate_token_valid(cli_auth_login):
    result = runner.invoke(
        app,
        ["token", "10"],
    )
    assert result.exit_code == 0
    token = result.stdout.splitlines()[2]
    # Verify that the cookie work.
    verification = verify_request(daeploy=None, authorization=f"Bearer {token}")
    assert verification == "OK"


def test_dae_test_command(tmp_path):
    result = runner.invoke(app, ["init", str(tmp_path)], input="test_project")
    assert result.exit_code == 0

    result = runner.invoke(app, ["test", str(tmp_path / "test_project")])
    print(result.stdout)  # Keep this here!
    assert result.exit_code == 0


def test_parse_var():
    assert parse_var("VAR=VAL") == ("VAR", "VAL")
    assert parse_var("VAR") == ("VAR", "")
    os.environ["VAR"] = "VAL_"
    assert parse_var("VAR") == ("VAR", "VAL_")
    assert parse_var('VAR="multi val"') == ("VAR", '"multi val"')
    assert parse_var("VAR=VAL=VALCONT") == ("VAR", "VAL=VALCONT")


def test_parse_vars():
    assert parse_vars([]) == {}
    assert parse_vars(["VAR=VAL", "ENVVAR"]) == {"VAR": "VAL", "ENVVAR": ""}
