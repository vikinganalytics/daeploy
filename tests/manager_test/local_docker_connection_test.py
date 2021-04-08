from datetime import datetime
from unittest import mock
from unittest.mock import patch
from async_generator import async_generator
import time
import pytest
import docker
import requests
import inspect


from manager.constants import DAEPLOY_FIRST_EXTERNAL_PORT
from manager.runtime_connectors import LocalDockerConnector
from manager.data_models.request_models import BaseService
from manager.data_models.response_models import (
    InspectResponse,
    StateResponse,
    NetworkSettingsResponse,
)


def kill_all_services_without_removing_images(con):
    for service in con.get_services():
        container = con.CLIENT.containers.get(service)
        container.remove(force=True)


@pytest.fixture
def local_docker_connection():
    try:
        con = LocalDockerConnector()

        # Kill any started service to get a "clean slate" for the test
        kill_all_services_without_removing_images(con)

        # Yield connection to the current test
        yield con
    finally:
        # Clean up after test
        kill_all_services_without_removing_images(con)


def test_starting_new_service(local_docker_connection):

    url = local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    assert int(url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT

    service = local_docker_connection.get_services()[0]
    version = service.split("-")[-1]
    name = service.split("-")[-2]
    assert name == "test"
    assert version == "0.1.0"


def test_start_image_service_with_docker_run_args(local_docker_connection):

    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
        docker_run_args={
            "name": "test_2",
            "privileged": True,
        },
    )

    service = local_docker_connection.get_services()[0]

    version = service.split("-")[-1]
    name = service.split("-")[-2]

    assert name == "test"  # Should not be "test_2"

    inspect = local_docker_connection.inspect_service(
        BaseService(name="test", version="0.1.0")
    )

    print(inspect)

    assert inspect["HostConfig"]["Privileged"]


def test_starting_two_service_different_version(local_docker_connection):

    first_url = local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    second_url = local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.2.0",
        internal_port=80,
    )

    assert int(first_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT
    assert int(second_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT + 1


def test_with_failing_services_port_allocation(local_docker_connection):
    # Reusing the external port numbers is according to expectation
    # This is not a problem in a production setup (i.e. with the manager)
    # running in a docker container but may cause some confusion in our local
    # development environment (i.e. when the manager runs directly in WSL)

    first_url = local_docker_connection.create_service(
        image="bash:latest",
        name="failing",
        version="0.1.0",
        internal_port=80,
        docker_run_args={"command": ["sh", "-c", "exit 1"]},
    )

    assert int(first_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT

    second_url = local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="running",
        version="0.1.0",
        internal_port=80,
    )

    assert int(second_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT

    time.sleep(1)

    response = requests.get(second_url)
    assert response.status_code == 200

    third_url = local_docker_connection.create_service(
        image="bash:latest",
        name="failing",
        version="0.2.0",
        internal_port=80,
        docker_run_args={"command": ["sh", "-c", "exit 1"]},
    )

    assert int(third_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT + 1

    fourth_url = local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="running",
        version="0.2.0",
        internal_port=80,
    )

    assert int(fourth_url.split(":")[-1]) == DAEPLOY_FIRST_EXTERNAL_PORT + 1

    time.sleep(1)

    response = requests.get(fourth_url)
    assert response.status_code == 200


def test_with_failing_services_restart(local_docker_connection):

    client = docker.from_env()

    local_docker_connection.create_service(
        image="bash:latest",
        name="late_failer",
        version="0.1.0",
        internal_port=80,
        docker_run_args={"command": ["sh", "-c", "sleep 6; exit 1"]},
    )

    local_docker_connection.create_service(
        image="bash:latest",
        name="early_failer",
        version="0.1.0",
        internal_port=80,
        docker_run_args={"command": ["sh", "-c", "sleep 3; exit 1"]},
    )

    time.sleep(6)

    insp1 = local_docker_connection.inspect_service(
        BaseService(name="late_failer", version="0.1.0")
    )
    insp2 = local_docker_connection.inspect_service(
        BaseService(name="early_failer", version="0.1.0")
    )

    assert insp1["State"]["Status"] == "running"
    assert insp2["State"]["Status"] == "exited"


@pytest.mark.asyncio
async def test_service_logs(local_docker_connection):

    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    service = BaseService(name="test", version="0.1.0")

    logs = local_docker_connection.service_logs(service)
    assert inspect.isasyncgen(logs)


def check_required_inspection_keys(container_info):
    assert set(InspectResponse.schema()["required"]).issubset(
        set(container_info.keys())
    )
    assert set(NetworkSettingsResponse.schema()["required"]).issubset(
        set(container_info["NetworkSettings"].keys())
    )
    assert set(StateResponse.schema()["required"]).issubset(
        set(container_info["State"].keys())
    )


def test_image_exist_in_running_service_image_exists(local_docker_connection):
    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    assert local_docker_connection.image_exists_in_running_service(
        "traefik/whoami", "latest"
    )


def test_image_exist_in_running_service_image_not_exists(local_docker_connection):
    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    assert not local_docker_connection.image_exists_in_running_service(
        "my_image", "latest"
    )


def test_remove_image_if_exists_false_if_image_being_used(local_docker_connection):
    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )
    res = local_docker_connection.remove_image_if_exists("traefik/whoami", "latest")
    assert not res


def test_remove_service_both_image_and_container_removed(local_docker_connection):
    local_docker_connection.create_service(
        image="traefik/whoami:latest",
        name="test",
        version="0.1.0",
        internal_port=80,
    )

    container_name = local_docker_connection.get_services()[0]
    images_before = local_docker_connection.CLIENT.images.list()
    containers_before = local_docker_connection.CLIENT.containers.list()

    service = BaseService(name="test", version="0.1.0")
    local_docker_connection.remove_service(service)

    images_after = local_docker_connection.CLIENT.images.list()
    containers_after = local_docker_connection.CLIENT.containers.list()

    assert len(images_before) > len(images_after)
    assert len(containers_before) > len(containers_after)

    assert container_name not in [c.name for c in containers_after]
    # Check that the image is removed.
    with pytest.raises(docker.errors.ImageNotFound):
        local_docker_connection.CLIENT.images.get("traefik/whoami:latest")


def test_manager_logs_no_container(local_docker_connection):
    with pytest.raises(RuntimeError):
        local_docker_connection.manager_logs(since=datetime.now())


def test_manager_logs_with_container(local_docker_connection):
    def fake_get_manager_container():
        class MockManagerContainer:
            def logs(self, since):
                return "All is well"

        return MockManagerContainer()

    local_docker_connection._get_manager_container = fake_get_manager_container
    logs = local_docker_connection.manager_logs(since=datetime.now())
    assert logs == "All is well"
