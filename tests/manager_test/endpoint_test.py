import asyncio
import pickle
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import pydantic
import pytest
from async_asgi_testclient import TestClient as AsyncTestClient
from docker.errors import ImageNotFound
from fastapi.testclient import TestClient
from manager import logging_api, notification_api, service_api, proxy
from manager.app import app
from manager.constants import DAEPLOY_DOCKER_BUILD_IMAGE, get_manager_version
from manager.data_models.request_models import BaseService
from manager.database.database import initialize_db, remove_db


client = TestClient(app)
async_client = AsyncTestClient(app)

TAR_FILE_NAME = "test_tar.gz"
IMAGE_TAR_FILE_NAME = "hello-world.tar"
PYTHON_FILE_NAME = "main.py"
PICKLE_FILE_NAME = "model.pkl"
SERVICE_NAME = "myservice"
SERVICE_VERSION = "0.0.1"


@pytest.fixture
def database():
    try:
        initialize_db()
        yield
    finally:
        remove_db()


@pytest.fixture
def python_file(tmp_path):
    filepath = tmp_path / PYTHON_FILE_NAME
    with open(filepath, "w") as file_handle:
        file_handle.write("")
    yield filepath


class TestModel:
    coeff = 2

    def predict(self, data):
        return self.coeff * data.iloc[0, :].to_numpy()


@pytest.fixture
def pickle_file(tmp_path):
    model = TestModel()
    filepath = tmp_path / PICKLE_FILE_NAME
    with open(filepath, "wb") as file_handle:
        pickle.dump(model, file_handle)
    yield filepath


@pytest.fixture
def tar_file(tmp_path, python_file):
    filepath = tmp_path / TAR_FILE_NAME
    with tarfile.open(filepath, "w:gz") as tar:
        tar.add(python_file)
    yield tar


@pytest.fixture(scope="module")
def remove_image_tar():
    try:
        yield
    finally:
        Path(IMAGE_TAR_FILE_NAME).unlink()


@pytest.fixture()
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


@pytest.fixture
def notifications_dict():
    try:
        # Reset notifications between tetsts
        notification_api.NOTIFICATIONS = {}
    finally:
        # Clean up after test
        notification_api.NOTIFICATIONS = {}


async def simple_generator():
    yield bytes("Log1 ", encoding="UTF-8")
    yield bytes("Log2 ", encoding="UTF-8")
    yield bytes("Log3 ", encoding="UTF-8")


@pytest.fixture
def clean_proxy_config():
    try:
        yield
    finally:
        proxy.remove_service_configuration(SERVICE_NAME, SERVICE_VERSION)


def test_root():
    response = client.get("/")
    assert response.status_code == 200


def test_version():
    response = client.get("/~version")
    assert response.status_code == 200
    assert response.json() == get_manager_version()


def test_post_notifications(notifications_dict):
    req = {
        "service_name": SERVICE_NAME,
        "service_version": SERVICE_VERSION,
        "msg": "Hello sir!",
        "severity": 0,
        "dashboard": True,
        "email": False,
        "timer": 0,
        "timestamp": "2020-01-01",
    }

    response = client.post("/notifications/", json=req)
    assert response.status_code == 200
    assert response.json() == "Notification added"


def test_get_delete_notifications(notifications_dict):
    response = client.get("/notifications")
    assert response.status_code == 200
    assert response.json() == {}
    req = {
        "service_name": SERVICE_NAME,
        "service_version": SERVICE_VERSION,
        "msg": "Hello sir!",
        "severity": 0,
        "dashboard": True,
        "emails": None,
        "timer": 0,
        "timestamp": "2020-01-01",
    }

    client.post("/notifications/", json=req)
    response = client.get("/notifications")
    notification_hash = list(response.json().keys())[0]
    req["counter"] = 1

    assert response.status_code == 200
    assert response.json()[notification_hash] == req

    # Clear the notifications
    response = client.delete("/notifications/")
    assert response.status_code == 200

    # Check that we have no notifications in store
    response = client.get("/notifications")
    assert response.status_code == 200
    assert response.json() == {}


@patch.object(service_api, "RTE_CONN")
def test_get_services_empty(mocked_docker_connection, database):
    service_api.get_all_services_db = MagicMock(return_value=[])
    mocked_docker_connection.configure_mock(**{"get_services.return_value": []})

    response = client.get("/services")

    mocked_docker_connection.get_services.assert_called_with()
    assert response.status_code == 200
    assert response.json() == []


@patch.object(service_api, "RTE_CONN")
def test_post_services_git_request(
    mocked_docker_connection, database, clean_proxy_config
):
    # Mock, Mock and Mock!
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.return_value": False,
        }
    )
    service_api.run_s2i = MagicMock(return_value=True)
    req = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "git_url": "https://github.com/sclorg/django-ex",
    }

    response = client.post("/services/~git", json=req)

    assert response.status_code == 202
    service_api.run_s2i.assert_called_with(
        url="https://github.com/sclorg/django-ex",
        build_image=DAEPLOY_DOCKER_BUILD_IMAGE,
        name=SERVICE_NAME,
        version=SERVICE_VERSION,
    )
    assert response.json() == "Accepted"


def test_upload_local_image_request(database, remove_image_tar):
    image = service_api.RTE_CONN.CLIENT.images.pull("hello-world")
    # If hello-world image does not exists (pull failed) we get an error
    # here when we try to get it.
    image = service_api.RTE_CONN.CLIENT.images.get("hello-world")
    # Save the hello-world image to tar.
    command = ["docker", "save", "--output", "hello-world.tar", "hello-world"]
    subprocess.run(command, stdout=None, stderr=None, check=True)
    # Remove hello-world image
    service_api.RTE_CONN.CLIENT.images.remove("hello-world")
    # Make sure that it is removed.
    with pytest.raises(ImageNotFound):
        service_api.RTE_CONN.CLIENT.images.get("hello-world")
    # Upload the iamge
    response = client.post(
        "/services/~upload-image",
        data={},
        files={
            "image": ("filename", open("hello-world.tar", "rb"), "application/x-gzip")
        },
    )
    assert response.status_code == 202
    assert "Image uploaded with tags: ['hello-world:latest']" in response.json()
    # Make sure that we can find the hello-world image locally.
    image = service_api.RTE_CONN.CLIENT.images.get("hello-world")


@patch.object(service_api, "RTE_CONN")
def test_post_services_image_request(
    mocked_docker_connection, database, clean_proxy_config
):
    # Mock it all :)
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.return_value": "http://localhost:8001",
        }
    )
    service_api.run_s2i = MagicMock(return_value=True)
    req = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "image": "my_image",
        "run_args": {"privileged": True},
    }

    response = client.post("/services/~image", json=req)

    assert response.status_code == 202
    assert response.json() == "Accepted"
    # The s2i method should not be called.
    service_api.run_s2i.assert_not_called()
    # Assert that the image used when creating the service is
    # the image in the request.
    mocked_docker_connection.create_service.assert_called_with(
        image="my_image",
        name=SERVICE_NAME,
        version=SERVICE_VERSION,
        internal_port=80,
        environment_variables=ANY,
        run_args={"privileged": True},
    )


@patch.object(service_api, "RTE_CONN")
def test_post_services_image_not_exists(
    mocked_docker_connection, database, clean_proxy_config
):
    # Mock it all :)
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.side_effect": ImageNotFound("Image not found"),
        }
    )
    service_api.run_s2i = MagicMock(return_value=True)
    req = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "image": "nonexistingimagethatdoesnotexist",
    }

    response = client.post("/services/~image", json=req)

    assert response.status_code == 404


@patch.object(service_api, "RTE_CONN")
def test_post_services_image_exists_in_running_service_error(
    mocked_docker_connection, clean_proxy_config
):
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": True,
        }
    )
    req = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "git_url": "https://github.com/vikinganalytics/daeploy_fetch_testing",
    }

    response = client.post("/services/~git", json=req)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Service with name: myservice and version: 0.0.1 already exists!"
    }


@patch.object(service_api, "RTE_CONN")
def test_post_service_container_exists_error(
    mocked_docker_connection, clean_proxy_config
):
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "container_exists.return_value": True,
        }
    )
    req = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "git_url": "https://github.com/vikinganalytics/daeploy_fetch_testing",
    }

    response = client.post("/services/~git", json=req)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Service with name: myservice and version: 0.0.1 already exists!"
    }


@patch.object(service_api, "RTE_CONN")
def test_service_delete(mocked_docker_connection, database):
    mocked_docker_connection.configure_mock(
        **{
            "remove_service.return_value": True,
            "remove_image_if_exists.return_value": True,
        }
    )
    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION
    response = client.delete(
        "/services/", json={"name": service_name, "version": service_version}
    )

    assert response.status_code == 200
    assert response.json() == "OK"
    mocked_docker_connection.remove_service.assert_called_with(
        BaseService(name=service_name, version=service_version)
    )
    mocked_docker_connection.remove_image_if_exists.assert_called_with(
        service_name, service_version
    )


@patch.object(service_api, "RTE_CONN")
def test_service_delete_keep_image(mocked_docker_connection, database):
    mocked_docker_connection.configure_mock(
        **{
            "remove_service.return_value": True,
            "remove_image_if_exists.return_value": True,
        }
    )
    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION
    response = client.delete(
        "/services/",
        json={"name": service_name, "version": service_version},
        params={"remove_image": False},
    )

    assert response.status_code == 200
    assert response.json() == "OK"
    mocked_docker_connection.remove_service.assert_called_with(
        BaseService(name=service_name, version=service_version)
    )
    mocked_docker_connection.remove_image_if_exists.assert_not_called()


@patch.object(service_api, "RTE_CONN")
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="Event loop not closing correctly"
)
async def test_service_logs_no_streaming(
    mocked_docker_connection,
):
    mocked_docker_connection.configure_mock(
        **{
            "service_logs.return_value": simple_generator(),
        }
    )

    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION
    with await async_client.get(
        f"/services/~logs?name={service_name}&version={service_version}&follow=False",
        stream=False,
    ) as response:

        assert response.status_code == 200
        assert response.text == "Log1 Log2 Log3 "
        mocked_docker_connection.service_logs.assert_called_with(
            BaseService(name=service_name, version=service_version), None, False, None
        )


@patch.object(service_api, "RTE_CONN")
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="Event loop not closing correctly"
)
async def test_service_logs_no_streaming_tailing(mocked_docker_connection):
    mocked_docker_connection.configure_mock(
        **{"service_logs.return_value": simple_generator()}
    )

    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION
    with await async_client.get(
        f"/services/~logs?name={service_name}&version={service_version}&follow=False&tail=2",
        stream=False,
    ) as response:
        assert response.status_code == 200
        mocked_docker_connection.service_logs.assert_called_with(
            BaseService(name=service_name, version=service_version), 2, False, None
        )


@patch.object(service_api, "RTE_CONN")
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.version_info < (3, 8), reason="Event loop not closing correctly"
)
async def test_service_logs_streaming(mocked_docker_connection):
    # Test infinite stream.
    # Insperation from: https://github.com/tiangolo/fastapi/issues/2006

    async def infinte_simple_generator():
        while True:
            await asyncio.sleep(0.01)
            yield bytes("Log", encoding="UTF-8")

    mocked_docker_connection.configure_mock(
        **{"service_logs.return_value": infinte_simple_generator()}
    )

    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION

    count = 0
    max_lines = 1000

    with await async_client.get(
        f"/services/~logs?name={service_name}&version={service_version}&follow=True",
        stream=True,
    ) as response:
        async for line in response.iter_content(3):
            if count > max_lines:
                break
            line = line.decode("utf-8").strip()
            assert line == "Log"
            count += 1
        mocked_docker_connection.service_logs.assert_called_with(
            BaseService(name=service_name, version=service_version), None, True, None
        )


@patch.object(service_api, "RTE_CONN")
def test_service_inspection(mocked_docker_connection):
    mocked_docker_connection.configure_mock(
        **{
            "inspect.return_value": "Very very very much information",
        }
    )

    service_name = SERVICE_NAME
    service_version = SERVICE_VERSION

    with pytest.raises(pydantic.ValidationError):
        client.get(
            f"/services/~inspection?name={service_name}&version={service_version}"
        )
        mocked_docker_connection.inspect.assert_called_with(
            BaseService(name=service_name, version=service_version)
        )


@patch.object(service_api, "RTE_CONN")
def test_post_service_tar_valid_tar(
    mocked_docker_connection, tar_file, database, clean_proxy_config
):
    # Mock, Mock and Mock!
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.return_value": False,
        }
    )
    data = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
    }

    response = client.post(
        "/services/~tar",
        data=data,
        files={"file": ("filename", open(tar_file.name, "rb"), "application/x-gzip")},
    )

    mocked_docker_connection.create_service.assert_called()
    assert response.status_code == 202


@patch.object(service_api, "RTE_CONN")
def test_post_service_tar_pyton_file(
    mocked_docker_connection, python_file, clean_proxy_config
):
    # Mock, Mock and Mock!
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.return_value": False,
        }
    )

    data = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
    }

    response = client.post(
        "/services/~tar",
        data=data,
        files={"file": ("filename", open(python_file, "rb"), "application/x-gzip")},
    )

    assert response.status_code == 406


@patch.object(service_api, "RTE_CONN")
def test_post_service_pickle_file(
    mocked_docker_connection, pickle_file, database, clean_proxy_config
):
    # Mock, Mock and Mock!
    mocked_docker_connection.configure_mock(
        **{
            "image_exists_in_running_service.return_value": False,
            "service_version_exists.return_value": False,
            "create_service.return_value": False,
        }
    )

    data = {
        "name": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "port": 80,
        "requirements": [],
    }

    response = client.post(
        "/services/~pickle",
        data=data,
        files={"file": ("filename", open(pickle_file, "rb"), "application/x-gzip")},
    )

    mocked_docker_connection.create_service.assert_called()
    assert response.status_code == 202


def test_get_manager_logs():
    # No manager container -> 404
    response = client.get("/logs")
    assert response.status_code == 404

    with patch.object(logging_api, "RTE_CONN") as mocked_docker_connection:
        mocked_docker_connection.configure_mock(
            **{
                "manager_logs.return_value": "All is well",
            }
        )
        response = client.get("/logs")
        assert response.text == "All is well"
        assert response.status_code == 200
