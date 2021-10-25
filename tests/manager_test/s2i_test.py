import pytest

from manager.routers.service_api import run_s2i
from manager.constants import DAEPLOY_DOCKER_BUILD_IMAGE
from manager.runtime_connectors import LocalDockerConnector
from manager.exceptions import S2iException

name = "my_model"
version = "0.0.1"
git_url_public = "https://github.com/sclorg/django-ex"
git_url_inaccessible = "https://dummy:dummy@github.com/secret_person/secret_repo"


def test_run_s2i_valid():
    expected_image_name = "my_model:0.0.1"
    connector = LocalDockerConnector()
    images_before = connector.CLIENT.images.list()

    image_name = run_s2i(
        url=git_url_public,
        build_image=DAEPLOY_DOCKER_BUILD_IMAGE,
        name=name,
        version=version,
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
            url=git_url_inaccessible,
            build_image=DAEPLOY_DOCKER_BUILD_IMAGE,
            name=name,
            version=version,
        )


def test_run_s2i_git_repo_invalid_build_image_s2iException():
    with pytest.raises(S2iException):
        run_s2i(
            url=git_url_inaccessible,
            build_image="this_image_should_not_exists",
            name=name,
            version=version,
        )
