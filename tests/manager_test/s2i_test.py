import pytest

from manager.routers.service_api import run_s2i
from manager.constants import DAEPLOY_DEFAULT_S2I_BUILD_IMAGE
from manager.runtime_connectors import LocalDockerConnector
from manager.exceptions import S2iException

NAME = "my_model"
VERSION = "0.0.1"
GIT_URL_PUBLIC = "https://github.com/sclorg/django-ex"
GIT_URL_INACCESSIBLE = "https://dummy:dummy@github.com/secret_person/secret_repo"
NONEXISTENT_BUILD_IMAGE = "this_image_should_not_exists"
INVALID_BUILD_IMAGE = "python:3.8-slim"


def test_run_s2i_valid():
    expected_image_name = "my_model:0.0.1"
    connector = LocalDockerConnector()
    images_before = connector.CLIENT.images.list()

    image_name = run_s2i(
        url=GIT_URL_PUBLIC,
        build_image=DAEPLOY_DEFAULT_S2I_BUILD_IMAGE,
        name=NAME,
        version=VERSION,
    )
    images_after = connector.CLIENT.images.list()
    image_id = connector.CLIENT.images.get(image_name).id

    assert image_name == expected_image_name
    # Check that there exists an image with the expected name.
    assert image_id
    assert len(images_before) < len(images_after) + 1


def test_run_s2i_git_repo_without_access_s2iException():
    with pytest.raises(S2iException):
        run_s2i(
            url=GIT_URL_INACCESSIBLE,
            build_image=DAEPLOY_DEFAULT_S2I_BUILD_IMAGE,
            name=NAME,
            version=VERSION,
        )


def test_run_s2i_git_repo_invalid_build_image_s2iException():
    with pytest.raises(S2iException):
        run_s2i(
            url=GIT_URL_PUBLIC,
            build_image=NONEXISTENT_BUILD_IMAGE,
            name=NAME,
            version=VERSION,
        )


def test_run_s2i_invalid_build_image_s2iException():
    with pytest.raises(S2iException):
        run_s2i(
            url=GIT_URL_PUBLIC,
            build_image=INVALID_BUILD_IMAGE,
            name=NAME,
            version=VERSION,
        )
