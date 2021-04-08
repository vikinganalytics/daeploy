import re
from typing import List, Dict, Union

import semver

from fastapi import Path, UploadFile
from pydantic import BaseModel, validator, HttpUrl
from manager.constants import DAEPLOY_DEFAULT_INTERNAL_PORT


class BaseService(BaseModel):
    name: str
    version: str

    # pylint: disable=no-self-use
    @validator("name")
    def must_adhere_to_docker_requirements(cls, name):
        # Only allow a name to contain lower case letters, numbers and underscore
        regex_pattern = re.compile("[a-z0-9_]+$")
        if not regex_pattern.match(name):
            raise ValueError(
                "can only contain lower case letters, numbers and underscores"
            )
        return name

    # pylint: disable=no-self-use
    @validator("version")
    def must_be_semver_string(cls, version):
        if not semver.VersionInfo.isvalid(version):
            raise ValueError("must be a semantic version string")
        return version


class BaseNewServiceRequest(BaseService):
    port: int = Path(default=DAEPLOY_DEFAULT_INTERNAL_PORT, gt=0)


class ServiceImageRequest(BaseNewServiceRequest):
    image: str
    docker_run_args: Dict = {}

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "image": "myimage",
                "docker_run_args": {},
            }
        }


class ServiceGitRequest(BaseNewServiceRequest):
    git_url: HttpUrl

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "git_url": "https://github.com/sclorg/django-ex",
            }
        }


class ServiceTarRequest(BaseNewServiceRequest):
    file: UploadFile

    class Config:
        schema_extra = {
            "example": {
                "name": "myservice",
                "version": "0.0.1",
                "port": 8000,
                "file": "mytar.gz.tar",
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
