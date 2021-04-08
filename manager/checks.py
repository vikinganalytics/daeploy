from functools import wraps
import requests

from fastapi import HTTPException
from docker.errors import NotFound


def check_service_exists_query_parameters(func):
    @wraps(func)
    def wrapper(name, version, *args, **kwargs):
        try:
            return func(name=name, version=version, *args, **kwargs)
        except (NotFound, requests.exceptions.ChunkedEncodingError):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Service with name: {name} "
                    + f"and version: {version} does not exists!",
                ),
            )

    return wrapper


def async_check_service_exists_query_parameters(func):
    @wraps(func)
    async def wrapper(name, version, *args, **kwargs):
        try:
            return await func(name=name, version=version, *args, **kwargs)
        except (NotFound, requests.exceptions.ChunkedEncodingError):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Service with name: {name} "
                    + f"and version: {version} does not exists!",
                ),
            )

    return wrapper


def check_service_exists_json_body(func):
    @wraps(func)
    def wrapper(service, *args, **kwargs):
        try:
            return func(service=service, *args, **kwargs)
        except (NotFound, requests.exceptions.ChunkedEncodingError):
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Service with name: {service.name} "
                    + f"and version: {service.version} does not exists!",
                ),
            )

    return wrapper
