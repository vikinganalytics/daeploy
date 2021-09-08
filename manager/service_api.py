import tarfile
import tempfile
import logging
import subprocess
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from pydantic import ValidationError

from cookiecutter.main import cookiecutter
from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from fastapi.responses import StreamingResponse
from docker.errors import ImageNotFound, ImageLoadError

from manager.exceptions import (
    DatabaseConflictException,
    DatabaseNoMatchException,
    DatabaseOutOfSyncException,
    S2iException,
)
from manager.runtime_connectors import create_image_name, RTE_CONN
from manager.data_models.request_models import (
    BaseNewServiceRequest,
    ServiceImageRequest,
    ServiceGitRequest,
    ServiceTarRequest,
    ServicePickleRequest,
    BaseService,
)
from manager.data_models.response_models import ServiceResponse, InspectResponse
from manager.constants import (
    DAEPLOY_SERVICE_AUTH_TOKEN_KEY,
    DAEPLOY_DOCKER_BUILD_IMAGE,
    DAEPLOY_PICKLE_FILE_NAME,
    DAEPLOY_PREFIX,
    DAEPLOY_TAR_FILE_NAME,
    DAEPLOY_DEFAULT_INTERNAL_PORT,
)
from manager.checks import (
    check_service_exists_json_body,
    check_service_exists_query_parameters,
    async_check_service_exists_query_parameters,
)
from manager import proxy
from manager.database import service_db
from manager.database.database import session_scope
from manager.auth_api import new_api_token, delete_token

THIS_DIR = Path(__file__).parent

LOGGER = logging.getLogger(__name__)

ROUTER = APIRouter()


@ROUTER.get("/", response_model=List[ServiceResponse])
def read_services():
    """
    Returns the currently running services as hosted by this daeploy instance

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    runtime_services = RTE_CONN.get_services()
    db_services = service_db.get_all_services_db()
    try:
        service_db.compare_runtime_db(runtime_services, db_services)
    except DatabaseOutOfSyncException as exc:
        raise HTTPException(
            status_code=412,
            detail=f"{str(exc)}",
        )
    return db_services


def check_service_exists(name: str, version: str):
    """Check if a service exists and raise an HTTP exception if they do

    Args:
        name (str): Name of the service
        version (str): Version of the service

    Raises:
        HTTPException: If service version exists in a running service
        HTTPException: If the same image exists in a running service
    """
    if RTE_CONN.service_version_exists(service=BaseService(name=name, version=version)):
        raise HTTPException(
            status_code=409,
            detail=f"Service with name: {name} and version: {version} already exists!",
        )

    if RTE_CONN.image_exists_in_running_service(name, version):
        raise HTTPException(
            status_code=409,
            detail=f"Image with name: {name} and version: {version} already exists!",
        )


def new_service_configuration(
    name: str, version: str, image: str, url: str, token: dict
):
    """Creates service configuration files for a new service

    Args:
        name (str): Name of the new service
        version (str): Version of the new service
        image (str): Image of the new service
        url (str): URL of the new service
        token (dict): Token of the new service
    """

    try:
        service_db.add_new_service_record(
            name=name,
            version=version,
            image=image,
            url=url,
            token_uuid=str(token["Id"]),
        )
    except DatabaseConflictException as exc:
        # We catch this error to allow a user to get back to the database state
        LOGGER.info(f"Service was not added to database because: {str(exc)}")
    main_version, shadow_versions = service_db.get_main_and_shadow_versions(name)

    # Configure proxy for service and mirroring
    proxy.create_new_service_configuration(name=name, version=version, address=url)
    proxy.create_mirror_configuration(name, main_version, shadow_versions)


@ROUTER.post("/~git", status_code=202)
def new_service_from_git_repo(service_request: ServiceGitRequest):
    """
    Create a new service from a git repository.

    \f
    # noqa: DAR101,DAR201,DAR401

    """

    # Unpack
    name = service_request.name
    version = service_request.version
    port = service_request.port

    check_service_exists(name, version)

    try:
        # Since s2i does not overwrite existing images,
        # remove the image if it exists.
        RTE_CONN.remove_image_if_exists(name, version)

        image = run_s2i(
            url=service_request.git_url,
            # TODO: We need to handle different build images.
            build_image=DAEPLOY_DOCKER_BUILD_IMAGE,
            name=name,
            version=version,
        )
    except S2iException as exc:
        raise HTTPException(
            status_code=422,
            detail=f"S2i failed with error: {exc}",
        )

    token = new_api_token()
    # We have a built image, lets spin it up
    url = RTE_CONN.create_service(
        image=image,
        name=name,
        version=service_request.version,
        internal_port=port,
        environment_variables={
            DAEPLOY_SERVICE_AUTH_TOKEN_KEY: token["Token"],
        },
    )

    new_service_configuration(name, version, image, url, token)

    return "Accepted"


def new_service_from_tmpdir(tmpdirname: str, service_request: BaseNewServiceRequest):
    """Start a new service from a directory using s2i

    Args:
        tmpdirname (str): Path to the temporary directory
        service_request (BaseNewServiceRequest): Request for the new service

    Raises:
        HTTPException: If s2i fails for some reason
    """
    name = service_request.name
    version = service_request.version

    check_service_exists(name, version)
    try:
        # Since s2i does not overwrite existing images,
        # remove the image if it exists.
        RTE_CONN.remove_image_if_exists(name, version)
        image = run_s2i(
            url=tmpdirname,
            build_image=DAEPLOY_DOCKER_BUILD_IMAGE,
            name=name,
            version=version,
        )
    except S2iException as exc:
        raise HTTPException(
            status_code=422,
            detail=f"S2i failed with error: {exc}",
        )

    token = new_api_token()
    # We have a built image, lets start the service
    url = RTE_CONN.create_service(
        image=image,
        name=name,
        version=version,
        internal_port=service_request.port,
        environment_variables={
            DAEPLOY_SERVICE_AUTH_TOKEN_KEY: token["Token"],
        },
    )

    new_service_configuration(name, version, image, url, token)


# pylint: disable=too-many-locals
@ROUTER.post("/~tar", status_code=202)
def new_service_from_tar_file(
    name: str = Form(...),
    version: str = Form(...),
    port: int = Form(DAEPLOY_DEFAULT_INTERNAL_PORT),
    file: UploadFile = File(...),
):
    """
    Create a new service from a tar file.

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    try:
        service_request = ServiceTarRequest(
            name=name,
            version=version,
            port=port,
            file=file,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=406, detail=f"Failed to validate input with error: {exc}"
        )

    with tempfile.TemporaryDirectory(prefix=f"{DAEPLOY_PREFIX}_") as tmpdirname:
        tarfile_path = Path(tmpdirname) / DAEPLOY_TAR_FILE_NAME
        with tarfile_path.open("wb") as target_file:
            target_file.write(file.file.read())
            target_file.close()

        # Checking if the file is a tar file
        if not tarfile.is_tarfile(tarfile_path):
            raise HTTPException(
                status_code=406,
                detail="Only tar files are accepted at this endpoint!",
            )

        tar = tarfile.open(tarfile_path)
        tar.extractall(path=tmpdirname)
        tar.close()
        tarfile_path.unlink()
        new_service_from_tmpdir(tmpdirname, service_request)

    return "Accepted"


# pylint: disable=too-many-locals
@ROUTER.post("/~pickle", status_code=202)
def new_service_from_pickle(
    name: str = Form(...),
    version: str = Form(...),
    port: int = Form(DAEPLOY_DEFAULT_INTERNAL_PORT),
    file: UploadFile = File(...),
    requirements: List[str] = Form([]),
):
    """
    Autogenerated service with a predict function. Requires the supplied
    pickle file to have a `predict(X)` method that can take a pandas dataframe
    `X` as input and should return an object that can be converted to a list
    using `list()`. The function expects a dictionary in a format that can
    be loaded as a pandas dataframe(see
    https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.from_dict.html).
    To make your own customized services, please refer to the documentation.

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    try:
        service_request = ServicePickleRequest(
            name=name,
            version=version,
            port=port,
            file=file,
            requirements=requirements,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=406, detail=f"Failed to validate input with error: {exc}"
        )

    with tempfile.TemporaryDirectory(prefix=f"{DAEPLOY_PREFIX}_") as tmpdirname:
        tmpdirname = Path(tmpdirname)
        pickle_path = tmpdirname / DAEPLOY_PICKLE_FILE_NAME
        with pickle_path.open("wb") as target_file:
            target_file.write(file.file.read())

        # Generate the service code
        project_name = f"{name}_{version.replace('.', '_')}"
        cookiecutter(
            str(THIS_DIR / "templates" / "daeploy_pickle_template/"),
            no_input=True,
            extra_context={"project_name": project_name},
            output_dir=str(tmpdirname),
        )

        # Move the pickle into the project file structure
        project_dir = tmpdirname / project_name
        Path(project_dir / "models").mkdir(exist_ok=True)
        pickle_path.replace(project_dir / "models" / DAEPLOY_PICKLE_FILE_NAME)

        # Add requirements to service
        requirements_file = project_dir / "requirements.txt"
        with requirements_file.open("a") as file_handle:
            for item in requirements:
                file_handle.write(f"{item}\n")

        new_service_from_tmpdir(project_dir, service_request)

    return "Accepted"


@ROUTER.post("/~upload-image", status_code=202)
def new_service_from_local_image(
    image: UploadFile = File(...),
):
    """
    Upload local docker image to manager host.

    The image can be saved to tar by running:

    docker save --output my_image.tar my_image

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    try:
        images = RTE_CONN.CLIENT.images.load(image.file)
    except ImageLoadError as exc:
        raise HTTPException(
            status_code=406, detail=f"Failed to load sent docker image: {exc}"
        )
    return f"Image uploaded with tags: {images[0].tags} and id: {images[0].id}"


@ROUTER.post("/~image", status_code=202)
def new_service_from_image(service_request: ServiceImageRequest):
    """
    Create a new service from a image.

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    # Unpack
    name = service_request.name
    version = service_request.version
    port = service_request.port

    check_service_exists(name, version)

    token = new_api_token()

    try:
        url = RTE_CONN.create_service(
            image=service_request.image,
            name=name,
            version=service_request.version,
            internal_port=port,
            environment_variables={
                DAEPLOY_SERVICE_AUTH_TOKEN_KEY: token["Token"],
            },
            docker_run_args=service_request.docker_run_args,
        )
    except ImageNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"{str(exc)}",
        )

    new_service_configuration(name, version, service_request.image, url, token)

    return "Accepted"


@ROUTER.delete("/")
@check_service_exists_json_body
def kill_service(service: BaseService, remove_image: bool = True):
    """
    Kill a running service.

    \f
    # noqa: DAR101,DAR201,DAR401

    """

    main_version, shadow_versions = service_db.get_main_and_shadow_versions(
        service.name
    )
    if main_version == service.version and len(shadow_versions) > 0:
        raise HTTPException(
            status_code=403,
            detail=(
                "Not allowed to kill main service while there are mutliple"
                " deployed versions of that service"
            ),
        )

    RTE_CONN.remove_service(service)
    if remove_image:
        RTE_CONN.remove_image_if_exists(service.name, service.version)

    try:
        with session_scope() as session:
            record = service_db.get_service_record(
                session, service.name, service.version
            )
            delete_token(record.token_uuid)
        service_db.delete_service_record(service.name, service.version)
    except DatabaseNoMatchException as exc:
        # We prevent this error to let the user sync up the DB and RTE
        LOGGER.info(f"Service was not deleted from database because: {str(exc)}")

    proxy.remove_service_configuration(service.name, service.version)

    # Write a new mirror configuration file if there are versions left of service
    main_version, shadow_versions = service_db.get_main_and_shadow_versions(
        service.name
    )
    if main_version is not None:
        proxy.create_mirror_configuration(service.name, main_version, shadow_versions)
    return "OK"


@ROUTER.put("/~assign")
@check_service_exists_json_body
def assign_main_service(service: BaseService):

    try:
        service_db.assign_main_version(service.name, service.version)
    except DatabaseNoMatchException as exc:
        raise HTTPException(status_code=404, detail=f"{str(exc)}")

    # Write a new mirror configuration file
    main_version, shadow_versions = service_db.get_main_and_shadow_versions(
        service.name
    )
    if main_version:
        proxy.create_mirror_configuration(service.name, main_version, shadow_versions)
    return "OK"


@ROUTER.get("/~logs", response_class=StreamingResponse)
@async_check_service_exists_query_parameters
async def read_service_logs(
    name: str,
    version: str,
    tail: Optional[int] = None,
    follow: Optional[bool] = False,
    since: Optional[datetime] = None,
) -> str:
    """
    Get the logs from a service

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    service = BaseService(name=name, version=version)
    logs_generator = RTE_CONN.service_logs(service, tail, follow, since)
    return StreamingResponse(
        logs_generator,
        media_type="text/plain",
        # We need to set this header to make sure that the
        # logs show up instantly on chrome. Disable buffering.
        headers={"X-Content-Type-Options": "nosniff"},
    )


@ROUTER.get("/~inspection", response_model=InspectResponse)
@check_service_exists_query_parameters
def inspect_service(name: str, version: str) -> str:
    """
    Get low-level information of a service

    \f
    # noqa: DAR101,DAR201,DAR401

    """
    service = BaseService(name=name, version=version)
    return RTE_CONN.inspect_service(service)


def run_s2i(url: str, build_image: str, name: str, version: str) -> str:
    """Creates an image of the source code located on the url.

    Args:
        url (str): URL to fetch code from
        build_image (str): Name of image to use as a builder image
        name (str): Service name
        version (str): Service version

    Raises:
        S2iException: If anything goes bad while building. Error message
            contains more detailed information.

    Returns:
        str: Name and tag assigned to the built image
    """
    image_name = create_image_name(name, version)
    # Construct the command.
    command = ["s2i", "build", url, build_image, image_name]

    try:
        LOGGER.info(f"Running s2i for service {name} {version}")
        # $ s2i build <source> <image> [<tag>] -e ENV=VAR
        output = subprocess.run(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
        )
        LOGGER.debug(output.stdout.decode())
    except subprocess.CalledProcessError as exc:
        LOGGER.exception("s2i failed!")
        output = exc.stdout.decode().split("\n")  # List of lines
        filtered_output = filter(lambda x: x.startswith("ERROR"), output)
        error_string = "\n".join(filtered_output)
        raise S2iException(error_string)
    except FileNotFoundError as exc:
        LOGGER.exception("s2i failed!")
        raise S2iException(str(exc))

    return image_name
