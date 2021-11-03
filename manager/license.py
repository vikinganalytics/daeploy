import logging
from typing import Callable
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from fastapi.requests import Request
from fastapi.responses import Response

from manager.constants import get_activation_key, DAEPLOY_DEFAULT_VALIDITY
from manager.routers.auth_api import verify_token
from manager.routers.notification_api import (
    _manager_notification,
    register_notification,
)
from manager.exceptions import AuthError

LOGGER = logging.getLogger(__name__)

PUBLIC_KEY = b"""-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDV+jOOK05wRiWPTKLdK61ISM3Q
A2TTVhGsd1+FJJ217iJi1knG7UI4UlvPOftDBILkGAzICu65UJ/B/b0boB9sgwe3
B6UVE6Lw0n0QP5XI2buZ8NFRinESL7S2PsDxZC+P4Fp/YdMtICCGbNV6bdS8uz27
IVe6HefpGgjjjDBWDwIDAQAB
-----END PUBLIC KEY-----"""

EXPIRATION_TIME = datetime.now(tz=timezone.utc) + timedelta(
    hours=DAEPLOY_DEFAULT_VALIDITY
)


def activation_key_reader_on_startup():
    """Runs on startup to read any potential token set as an env variable"""
    activate(get_activation_key())


def activate(token: str):
    """Activate the application using a JWT token

    Args:
        token (str): Activation key in the form of a signed JWT token
    """
    global EXPIRATION_TIME  # pylint: disable=global-statement

    try:
        payload = verify_token(token, PUBLIC_KEY)
    except AuthError:
        LOGGER.warning("Could not read activation key successfully!")
        return

    expiration = payload.get("exp")
    if expiration:
        EXPIRATION_TIME = datetime.fromtimestamp(expiration, tz=timezone.utc)

    msg = (
        "Activation code read successfully,"
        f" validity time updated to: {EXPIRATION_TIME}"
    )
    LOGGER.info(msg)
    register_notification(_manager_notification(msg))


async def validity_door_man(request: Request, call_next: Callable) -> Response:
    """Starlette middleware used to intercept any HTTP calls to the manager after the
     validity period has expired.

    Args:
        request (Request): Incoming request
        call_next (Callable): Handle to next function in line

    Raises:
        HTTPException: If variable in license has expired

    Returns:
        Response: Appropriate response depening on validity period
    """
    # https://github.com/encode/starlette/issues/1099

    if datetime.now(tz=timezone.utc) > EXPIRATION_TIME:
        LOGGER.info(
            "Activation key is expired, intercepting all HTTP calls to manager!"
        )
        raise HTTPException(
            status_code=403, detail=str("Your activation key has expired!")
        )

    return await call_next(request)
