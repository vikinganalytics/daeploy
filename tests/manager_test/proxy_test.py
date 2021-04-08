import os
import time
from pathlib import Path
from unittest.mock import MagicMock
import requests

import docker
import pytest
import toml

from manager import app as root
import manager.proxy as pr

THIS_DIR = Path(__file__).parent
os.environ["DAEPLOY_PROXY_HTTP_PORT"] = "5080"
os.environ["DAEPLOY_PROXY_HTTPS_PORT"] = "5443"


@pytest.fixture
def traefik(tmp_path):
    os.environ["DAEPLOY_PROXY_CONFIG_PATH"] = str(tmp_path)
    killer = pr.initial_setup()
    time.sleep(1)  # Grace period
    try:
        yield
    finally:
        killer()


@pytest.fixture
def dummy_service():
    client = docker.from_env()
    container = client.containers.run(
        "traefik/whoami:latest", ports={80: 6000}, detach=True
    )
    try:
        yield container
    finally:
        container.remove(force=True)


@pytest.fixture
def dummy_service_2():
    client = docker.from_env()
    container = client.containers.run(
        "traefik/whoami:latest", ports={80: 6001}, detach=True
    )
    try:
        yield container
    finally:
        container.remove(force=True)


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
        ports={80: 80},
        volumes={
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"}
        },
        auto_remove=True,
    )
    time.sleep(2)  # Grace period
    try:
        yield container
    finally:
        container.remove(force=True)
        client.images.remove(image.id, force=True)


def test_default_config_traefik_dashboard(traefik):
    response = requests.get("http://localhost:5080/proxy/dashboard/")
    assert response.status_code == 200


def test_default_config_traefik_api(traefik):
    response = requests.get("http://localhost:5080/api/overview")
    assert response.status_code == 200


def test_default_config_routers(traefik, pinned):
    response = requests.get("http://localhost:5080/api/http/routers")
    assert response.json() == pinned


def test_default_config_middlewares(traefik, pinned):
    response = requests.get("http://localhost:5080/api/http/middlewares")
    assert response.json() == pinned


def test_default_config_services(traefik, pinned):
    response = requests.get("http://localhost:5080/api/http/services")
    assert response.json() == pinned


def test_with_dynamic_service(traefik, dummy_service, pinned):
    pr.create_new_service_configuration(
        "dummy_service", "1.0.0", "http://localhost:6000"
    )
    time.sleep(1)

    # Check service is up
    response = requests.get("http://localhost:6000")
    assert response.status_code == 200

    # Check if config is updated
    response = requests.get("http://localhost:5080/api/http/routers")
    assert response.json() == pinned

    # Check that service is reachable through proxy
    response = requests.get("http://localhost:5080/services/dummy_service_1.0.0")
    assert response.status_code == 200


def test_shadow_deploy_routing(traefik, dummy_service, dummy_service_2):
    pr.create_new_service_configuration(
        "dummy_service", "1.0.0", "http://localhost:6000"
    )
    time.sleep(1)

    response = requests.get("http://localhost:6000")
    assert response.status_code == 200

    response_100 = requests.get("http://localhost:5080/services/dummy_service_1.0.0")
    assert response_100.status_code == 200

    pr.create_new_service_configuration(
        "dummy_service", "2.0.0", "http://localhost:6001"
    )
    time.sleep(1)
    response_200 = requests.get("http://localhost:5080/services/dummy_service_2.0.0")
    assert response_200.status_code == 200

    pr.create_mirror_configuration("dummy_service", "1.0.0", ["2.0.0"])
    time.sleep(1)
    response = requests.get("http://localhost:5080/services/dummy_service")
    assert response.status_code == 200

    assert response.content[:30] == response_100.content[:30]
    assert response.content[:30] != response_200.content[:30]


def test_initial_setup_creates_existing_service_configs(tmp_path):
    services = [
        {"name": "1", "version": "1.0.0", "url": "url1", "main": True},
        {"name": "1", "version": "1.1.0", "url": "url2", "main": False},
        {"name": "2", "version": "1.0.1", "url": "url3", "main": True},
    ]
    side_effects = [
        (
            "1.0.0",
            ["1.1.0"],
        ),
        (
            "1.0.1",
            [],
        ),
    ]
    root.service_db.get_all_services_db = MagicMock(return_value=services)
    root.service_db.get_main_and_shadow_versions = MagicMock(side_effect=side_effects)
    os.environ["DAEPLOY_PROXY_CONFIG_PATH"] = str(tmp_path)
    killer = pr.initial_setup()
    root.recreate_proxy_configurations()
    time.sleep(1)  # Grace period
    try:
        proxy_files = os.listdir(tmp_path / "dynamic")
        assert "1_configuration.toml" in proxy_files
        assert "1_1.0.0_configuration.toml" in proxy_files
        assert "1_1.1.0_configuration.toml" in proxy_files
        assert "2_configuration.toml" in proxy_files
        assert "2_1.0.1_configuration.toml" in proxy_files
    finally:
        killer()


def test_https_dynamic_config_services(tmp_path, pinned):
    services = [
        {"name": "1", "version": "1.0.0", "url": "url1", "main": True},
    ]
    side_effects = [("1.0.0", [])]
    root.service_db.get_all_services_db = MagicMock(return_value=services)
    root.service_db.get_main_and_shadow_versions = MagicMock(side_effect=side_effects)
    os.environ["DAEPLOY_PROXY_CONFIG_PATH"] = str(tmp_path)
    os.environ["DAEPLOY_PROXY_HTTPS"] = "true"
    # Prevent traefik from starting to not run out of certificates from tests
    pr.run_proxy = MagicMock()
    killer = pr.initial_setup()
    root.recreate_proxy_configurations()
    time.sleep(1)  # Grace period
    try:
        with open(tmp_path / "dynamic" / "1_configuration.toml", "r") as f:
            service_config = toml.load(f)
        assert service_config == pinned
    finally:
        killer()
        os.environ["DAEPLOY_PROXY_HTTPS"] = "false"


def test_https_static_config(tmp_path, pinned):
    os.environ["DAEPLOY_PROXY_CONFIG_PATH"] = str(tmp_path)
    os.environ["DAEPLOY_PROXY_HTTPS"] = "true"
    # Prevent traefik from starting to not run out of certificates from tests
    pr.run_proxy = MagicMock()
    killer = pr.initial_setup()
    try:
        with open(tmp_path / "traefik.toml", "r") as f:
            static_config = toml.load(f)

        https_config = {}
        https_config["certificatesResolvers"] = static_config["certificatesResolvers"]
        https_config["certificatesResolvers"]["cert-resolver"]["acme"].pop("storage")
        https_config["entryPoints"] = static_config["entryPoints"]
        assert https_config == pinned

    finally:
        killer()
        os.environ["DAEPLOY_PROXY_HTTPS"] = "false"
