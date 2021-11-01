import re
from typing import List, Dict, Union

import semver
from pydantic.types import SecretStr
from pydantic import BaseModel, validator, HttpUrl
from fastapi import Path, UploadFile

from manager.constants import (
    DAEPLOY_DEFAULT_INTERNAL_PORT,
    DAEPLOY_DEFAULT_S2I_BUILD_IMAGE,
)


class BaseService(BaseModel):
    name: str
    version: str

    # pylint: disable=no-self-use
    @validator("name")
    def must_adhere_to_docker_requirements(cls, name):
        # Only allow a name to contain lower case letters, numbers and underscore
        # anywhere but in the beginning and end
        regex_pattern = re.compile("^(?!_)[a-z0-9_]+(?<!_)$")
        if not regex_pattern.match(name):
            raise ValueError(
                "Name can only contain lower case letters, numbers and underscores,"
                " but should not start or end with an underscore."
            )
        return name

    # pylint: disable=no-self-use
    @validator("version")
    def must_be_semver_string(cls, version):
        if not semver.VersionInfo.isvalid(version):
            raise ValueError("Version must be a semantic version string.")
        return version


class BaseNewServiceRequest(BaseService):
    port: int = Path(default=DAEPLOY_DEFAULT_INTERNAL_PORT, gt=0)
    run_args: Dict = {}


class BaseNewS2IServiceRequest(BaseNewServiceRequest):
    s2i_build_image: str = DAEPLOY_DEFAULT_S2I_BUILD_IMAGE


class ServiceImageRequest(BaseNewServiceRequest):
    image: str

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "image": "myimage",
                "run_args": {},
            }
        }


class ServiceGitRequest(BaseNewS2IServiceRequest):
    git_url: HttpUrl

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "git_url": "https://github.com/sclorg/django-ex",
                "run_args": {},
            }
        }


class ServiceTarRequest(BaseNewS2IServiceRequest):
    file: UploadFile

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "file": "mytar.gz.tar",
                "run_args": {},
            }
        }


class ServicePickleRequest(ServiceTarRequest):
    requirements: List[str]

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "file": "mymodel.pkl",
                "requirements": [],
            }
        }


class NotificationRequest(BaseModel):
    service_name: str
    service_version: str
    msg: str
    severity: int
    dashboard: bool
    emails: Union[List[str], None]
    timer: int
    timestamp: str

    def __hash__(self):
        return hash(
            (
                self.service_name,
                self.service_version,
                self.msg,
                self.severity,
                self.dashboard,
                self.timer,
            )
        )


class UserRequest(BaseModel):
    password: SecretStr
