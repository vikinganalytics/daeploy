import docker
import pytest
import time
import requests
import uuid
import datetime
import zipfile
import io
import re
import shutil

from setuptools import sandbox
from pathlib import Path
from typer.testing import CliRunner
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

import daeploy.cli.config as config
from daeploy.cli.cli import app

THIS_DIR = Path(__file__).parent
DAEPLOY_ROOT = THIS_DIR.parent.parent

WHEEL_FILE_NAME = "daeploy-0.0.0.dev0-py3-none-any.whl"
ADMIN_PASSWORD = "nisse123"

runner = CliRunner()


@pytest.fixture(scope="module")
def dummy_manager():
    client = docker.from_env()
    # Build new manage image specifically for these tests
    image, _ = client.images.build(
        path=str(THIS_DIR.parent.parent), tag="dummy_manager:latest", forcerm=True
    )
    container = client.containers.run(
        image,
        name="dummy_manager",
        detach=True,
        ports={80: 80, 443: 443},
        environment={
            "DAEPLOY_HOST_NAME": "localhost",
            "DAEPLOY_AUTH_ENABLED": True,
            "DAEPLOY_ADMIN_PASSWORD": ADMIN_PASSWORD,
        },
        volumes={
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}
        },
    )
    time.sleep(5)  # Grace period
    try:
        yield container
    finally:
        container.remove(force=True)
        client.images.remove(image.id, force=True)


@pytest.fixture(scope="module")
def cli_auth():
    config.initialize_cli_configuration()
    try:
        yield
    finally:
        config.CONFIG_FILE.unlink()


@pytest.fixture(scope="module")
def cli_auth_login(dummy_manager, cli_auth):
    runner.invoke(app, ["login"], input=f"http://localhost\nadmin\n{ADMIN_PASSWORD}\n")
    yield


@pytest.fixture(scope="module")
def pickle_service(cli_auth_login, headers):
    data = {
        "name": "pickle",
        "version": "0.1.0",
        "port": 8000,
        "requirements": ["pandas", "sklearn"],
    }

    requests.request(
        "POST",
        url="http://localhost/services/~pickle",
        data=data,
        headers=headers,
        files={"file": ("filename", open(THIS_DIR / "pickle_e2e_testing.pkl", "rb"))},
    )
    time.sleep(5)  # Grace period
    try:
        yield
    finally:
        runner.invoke(app, ["kill", "-a"], input="y")


@pytest.fixture(scope="module")
def services(cli_auth_login):
    """Generate upstream and downstream services for tests.
    Removes the created zip while for the services.
    Removes the wheel file of the daeploy package needed for the services.
    """
    for service in ["upstream", "downstream"]:
        generate_requirements_file_for_service(THIS_DIR / service)
        runner.invoke(app, ["deploy", service, "0.1.0", str(THIS_DIR / service)])
        time.sleep(5)  # Grace period
    try:
        yield
    finally:
        # Cleaning
        time.sleep(2)
        runner.invoke(app, ["kill", "-a"], input="y")
        (THIS_DIR / "upstream" / WHEEL_FILE_NAME).unlink()
        (THIS_DIR / "downstream" / WHEEL_FILE_NAME).unlink()
        try:
            (THIS_DIR / "upstream.tar.gz").unlink()
            (THIS_DIR / "downstream.tar.gz").unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def init_service(cli_auth_login, tmp_path):
    service_name = "test_project"
    try:
        runner.invoke(app, ["init", str(tmp_path)], input=service_name)
        (tmp_path / "test_project" / "requirements.txt").unlink()
        generate_requirements_file_for_service(tmp_path / "test_project")
        runner.invoke(
            app, ["deploy", service_name, "0.1.0", str(tmp_path / service_name)]
        )
        time.sleep(5)  # Grace period
        yield
    finally:
        time.sleep(2)
        runner.invoke(app, ["kill", "-a"], input="y")


@pytest.fixture(scope="module")
def token(cli_auth_login):
    result = runner.invoke(app, ["token"])
    return result.stdout.splitlines()[-1]


@pytest.fixture(scope="module")
def headers(token):
    headers = {
        "Authorization": f"Bearer {token}",
        "Host": "localhost",
    }
    return headers


@pytest.fixture(scope="module")
def logs(headers):
    def get_logs_from_service(service):
        url = (
            f"http://localhost/services/~logs?name={service}&version=0.1.0&follow=False"
        )
        logs = requests.request("GET", url=url, headers=headers).text
        return logs

    return get_logs_from_service


def generate_requirements_file_for_service(service_folder):
    """Fills in the requirements.txt for the services with
    the path to the wheel file which contains the daeploy package.
    """
    # TODO: No need to run the setup twice...
    sandbox.run_setup(
        str(THIS_DIR.parent.parent / "setup.py"),
        ["bdist_wheel", "--dist-dir", str(service_folder)],
    )
    with (service_folder / "requirements.txt").open("w") as file_handle:
        file_handle.write(WHEEL_FILE_NAME)


# This test is included in the e2e tests since it need to have a Manager
# running as a docker container. Otherwise, the version cannot be fetched.
def test_version_command_cli(dummy_manager, cli_auth_login):
    result = runner.invoke(
        app,
        ["--version"],
    )
    assert result.exit_code == 0
    assert "SDK version: 0.0.0.dev0" in result.stdout
    assert "Manager version: latest" in result.stdout


def test_manager_restart_ok(dummy_manager, headers):

    assert requests.get("http://localhost", headers=headers).status_code == 200

    dummy_manager.restart()
    time.sleep(5)  # Grace period

    assert requests.get("http://localhost", headers=headers).status_code == 200


def test_manager_logs(dummy_manager, headers):
    response = requests.request(
        "GET",
        url="http://localhost/logs",
        headers=headers,
    )
    assert response.status_code == 200
    assert "Application startup complete" in response.text


def test_deploy_manager_and_two_services(dummy_manager, cli_auth_login, services):
    client = docker.from_env()
    containers = [con.name for con in client.containers.list()]
    assert "daeploy-downstream-0.1.0" in containers
    assert "daeploy-upstream-0.1.0" in containers
    assert "dummy_manager" in containers


def test_reaching_daeploy_entrypoint(dummy_manager, cli_auth_login, services, headers):
    data = {"name": "Ragnar Lothbrok"}
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/hello",
        json=data,
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == "Hello Ragnar Lothbrok"


def test_reaching_daeploy_entrypoint_with_basemodel_args(
    dummy_manager, cli_auth_login, services, headers
):
    data = {
        "name": {"name": "Someone", "sirname": "Someoneson"},
        "info": {"age": 100, "height": 100},
    }
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/function_with_basemodel_args",
        json=data,
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "age": 100,
        "height": 100,
        "name": "Someone",
        "sirname": "Someoneson",
    }


def test_call_service_multiple_cases(
    dummy_manager, cli_auth_login, services, logs, headers
):
    url = "http://localhost/services/upstream/"
    url_downstream_post = url + "call_downstream_method"
    url_downstream_get = url + "call_downstream_get_method"

    unique_name = str(uuid.uuid1())

    # Correct arguments
    resp = requests.request(
        "POST",
        url=url_downstream_post,
        json={
            "service_name": "downstream",
            "entrypoint_name": "hello",
            "arguments": {"name": f"{unique_name}"},
        },
        headers=headers,
    )
    downstream_logs = logs("downstream")
    upstream_logs = logs("upstream")
    assert resp.status_code == 200
    assert resp.json() == f"Hello {unique_name}"
    assert "Calling entrypoint: hello in service: downstream" in upstream_logs
    assert (
        f'Response from entrypoint: "Hello {unique_name}", code: 200' in upstream_logs
    )
    assert f"Greeting someone with the name: {unique_name}" in downstream_logs

    # Wrong argument types
    unique_name = str(uuid.UUID)
    resp = requests.request(
        "POST",
        url=url_downstream_post,
        json={
            "service_name": "downstream",
            "entrypoint_name": "hello",
            "arguments": {"name": [f"{unique_name}", "Another Viking"]},
        },
        headers=headers,
    )
    assert resp.status_code == 500
    downstream_logs = logs("downstream")
    assert "422 Unprocessable Entity" in downstream_logs

    # Wrong argument keys
    unique_name = str(uuid.uuid1())
    resp = requests.request(
        "POST",
        url=url_downstream_post,
        json={
            "service_name": "downstream",
            "entrypoint_name": "hello",
            "arguments": {"age": f"{unique_name}"},
        },
        headers=headers,
    )
    assert resp.status_code == 500
    downstream_logs = logs("downstream")
    assert "422 Unprocessable Entity" in downstream_logs

    # Call existing service but non-existing method
    unique_name = str(uuid.uuid1())
    resp = requests.request(
        "POST",
        url=url_downstream_post,
        json={
            "service_name": "downstream",
            "entrypoint_name": "hello_TYPO",
            "arguments": {"name": f"{unique_name}"},
        },
        headers=headers,
    )
    assert resp.status_code == 500
    downstream_logs = logs("downstream")
    assert "Not Found" in downstream_logs

    # Call non existing service
    unique_name = str(uuid.uuid1())
    resp = requests.request(
        "POST",
        url=url_downstream_post,
        json={
            "service_name": "downstream_TYPO",
            "entrypoint_name": "hello",
            "arguments": {"name": f"{unique_name}"},
        },
        headers=headers,
    )
    assert resp.status_code == 500
    upstream_logs = logs("upstream")
    assert "Not Found" in upstream_logs


    # Call get method
    resp = requests.request(
        "POST",
        url=url_downstream_get,
        json={
            "service_name": "downstream",
        },
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json() == "Get - Got - Gotten"


def test_raised_notification_from_service_ends_up_at_manager(
    dummy_manager, cli_auth_login, services, headers
):
    # Trigger the notification
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/raise_notification",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json() == "Done"

    # Get the notifications from the manager
    resp = requests.request(
        "GET",
        url="http://localhost/notifications",
        headers=headers,
    )

    expected_notification = {
        "service_name": "downstream",
        "service_version": "0.1.0",
        "msg": "Notification raised...",
        "severity": 1,
        "dashboard": True,
        "emails": None,
        "timer": 0,
        "counter": 1,
    }

    assert resp.status_code == 200
    # We should only have one notification
    assert len(resp.json().keys()) == 1
    # Get the only notification
    notification = list(resp.json().values())[0]
    # Delete the timestamp so that it can be compared with the expected notification.
    del notification["timestamp"]
    assert notification == expected_notification

    # Trigger the notifcation again and verify that we increase the count field.
    requests.request(
        "POST",
        url="http://localhost/services/downstream/raise_notification",
        headers=headers,
    )
    # Get the notifications again.
    resp = requests.request(
        "GET",
        url="http://localhost/notifications",
        headers=headers,
    )
    # We should only have one notification
    assert len(resp.json().keys()) == 1
    # Get the only notification
    notification = list(resp.json().values())[0]
    # Delete the timestamp so that it can be compared with the expected notification.
    del notification["timestamp"]
    # Increase the counter in the expected_notificaion
    expected_notification["counter"] = 2
    assert notification == expected_notification


def test_docs_page_from_service_shows_correct_docs(
    dummy_manager, cli_auth_login, services, headers
):
    service_docs = requests.request(
        "GET",
        url="http://localhost/services/downstream/docs",
        headers=headers,
    )

    manager_docs = requests.request(
        "GET",
        url="http://localhost/docs",
        headers=headers,
    )

    # Test documentation started properly
    response = requests.get("http://localhost/services/downstream/openapi.json")
    assert response.status_code == 200

    response = requests.get("http://localhost/openapi.json")
    assert response.status_code == 200

    assert service_docs.status_code == manager_docs.status_code == 200
    assert service_docs.text != manager_docs.text
    assert "downstream" in service_docs.text
    assert "0.1.0" in service_docs.text


def test_service_from_pickle_endpoint(dummy_manager, pickle_service, headers):
    client = docker.from_env()
    containers = [con.name for con in client.containers.list()]
    assert "daeploy-pickle-0.1.0" in containers

    data = {"data": {"1": [1, 1], "2": [2, 2], "3": [3, 3], "4": [4, 4]}}

    resp = requests.request(
        "POST",
        url="http://localhost/services/pickle/predict",
        json=data,
        headers=headers,
    )
    assert resp.status_code == 200

    # Test documentation started properly
    response = requests.get("http://localhost/services/pickle/openapi.json")
    assert response.status_code == 200


def test_monitored_variables_json(dummy_manager, services, headers):
    # Trigger to storing
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/store_variables_10_times",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200
    time.sleep(1)

    # Check response from json monitoring endpoint
    resp = requests.request(
        "GET",
        url="http://localhost/services/downstream/~monitor",
        json={},
        headers=headers,
    )
    data = resp.json()
    assert "v1" in data.keys() and "v2" in data.keys()
    assert list(data["v1"].keys()) == ["timestamp", "value"]
    assert list(data["v2"].keys()) == ["timestamp", "value"]
    assert len(data["v1"]["timestamp"]) == len(data["v1"]["value"]) == 10
    assert len(data["v2"]["timestamp"]) == len(data["v2"]["value"]) == 10

    last_ts = data["v1"]["timestamp"][-1]
    last_value = data["v1"]["value"][-1]

    # Query only v1 and only the latest entry of v1
    resp = requests.request(
        "GET",
        url=f"http://localhost/services/downstream/~monitor?start={last_ts}&end={datetime.datetime.utcnow()}&variables=v1",
        headers=headers,
    )
    data = resp.json()
    assert ["v1"] == list(data.keys())
    assert len(data["v1"]["timestamp"]) == len(data["v1"]["value"]) == 1
    assert data["v1"]["value"] == [last_value]


def test_monitored_variables_csv(dummy_manager, services, headers):
    # Trigger to storing
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/store_variable_vz_10_times",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200
    time.sleep(1)

    # Check response from json monitoring endpoint
    resp = requests.request(
        "GET",
        url="http://localhost/services/downstream/~monitor/csv",
        json={},
        headers=headers,
        stream=True,
    )
    zip_file = zipfile.ZipFile(io.BytesIO(resp.content))
    assert "vz.csv" in zip_file.namelist()
    with zip_file.open("vz.csv") as myfile:
        lines = myfile.readlines()
        lines = [line.decode("utf-8").split() for line in lines]

        # Check that the csv has the correct headers
        assert lines[0] == ["timestamp,value"]
        assert len(lines) == 11


def test_monitored_variables_db(dummy_manager, services, headers):
    # Trigger to storing
    resp = requests.request(
        "POST",
        url="http://localhost/services/downstream/store_variables_10_times",
        json={},
        headers=headers,
    )
    assert resp.status_code == 200
    time.sleep(1)

    # Check response from json monitoring endpoint
    resp = requests.request(
        "GET",
        url="http://localhost/services/downstream/~monitor/db",
        json={},
        headers=headers,
        stream=True,
    )
    assert "SQLite format" in resp.text
    assert resp.headers["Content-Disposition"] == 'attachment; filename="database.db"'


def test_service_from_daeploy_init(dummy_manager, init_service, headers):
    client = docker.from_env()
    containers = [con.name for con in client.containers.list()]
    assert "daeploy-test_project-0.1.0" in containers

    # Check hello endpoint
    name = {"name": "Rune Skejp"}
    resp = requests.request(
        "POST",
        url="http://localhost/services/test_project/hello",
        json=name,
        headers=headers,
    )
    assert resp.json() == "Hello Rune Skejp"

    # Check changing parameter
    value = {"value": "Wazzup"}
    resp = requests.request(
        "POST",
        url="http://localhost/services/test_project/~parameters/greeting_phrase",
        json=value,
        headers=headers,
    )

    resp = requests.request(
        "POST",
        url="http://localhost/services/test_project/hello",
        json=name,
        headers=headers,
    )
    assert resp.json() == "Wazzup Rune Skejp"

    # Check notification
    world = {"name": "World"}
    resp = requests.request(
        "POST",
        url="http://localhost/services/test_project/hello",
        json=world,
        headers=headers,
    )

    resp = requests.request(
        "GET",
        url="http://localhost/notifications",
        headers=headers,
    )

    assert resp.status_code == 200
    # We should only have one notification
    expected_notification = {
        "service_name": "test_project",
        "service_version": "0.1.0",
        "msg": "Someone is trying to greet the World, too time consuming. Skipping!",
        "severity": 1,
        "dashboard": True,
        "emails": None,
        "timer": 0,
        "counter": 1,
    }
    notification = list(resp.json().values())[-1]
    del notification["timestamp"]
    print(notification)
    assert expected_notification == notification

    # Test documentation started properly
    response = requests.get("http://localhost/services/test_project/openapi.json")
    assert response.status_code == 200


def test_notebook_service(dummy_manager, headers):
    host = headers["Host"]
    token_ = headers["Authorization"].split(" ")[-1]

    notebook_filename = (
        THIS_DIR.parent.parent
        / "docs"
        / "source"
        / "content"
        / "advanced_tutorials"
        / "daeploy_notebook_service.ipynb"
    )

    with open(notebook_filename) as file_handle:
        notebook = nbformat.read(file_handle, as_version=4)

    # Fill in the HOST and TOKEN variables with proper values
    original_cell = notebook["cells"][2]["source"]
    new_cell = re.sub(
        'HOST = "http://localhost"', f'HOST = "http://{host}"', original_cell
    )
    new_cell = re.sub('TOKEN = ""', f'TOKEN = "{token_}"', new_cell)

    notebook["cells"][2]["source"] = new_cell

    nb_executor = ExecutePreprocessor(timeout=600, kernel_name="python3")

    nb_executor.preprocess(
        notebook, {"metadata": {"path": str(notebook_filename.parent)}}
    )

    shutil.rmtree(notebook_filename.parent / "notebook_service")
