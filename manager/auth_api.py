import string
import random
import logging
import datetime
from uuid import uuid4, UUID
from typing import Optional, Union, List

import jwt
import bcrypt
from fastapi import APIRouter, Form, Request, Cookie, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import SecretStr

from manager.data_models.response_models import TokenResponse
from manager.constants import (
    auth_enabled,
    get_external_proxy_url,
    DAEPLOY_REQUIRED_PASSWORD_LENGTH,
)
from manager.database import auth_db, config_db
from manager.exceptions import DatabaseNoMatchException

ROUTER = APIRouter()

LOGGER = logging.getLogger(__name__)

TEMPLATES = Jinja2Templates(directory="manager/templates")


def generate_random_password() -> str:
    """Generate a random password consisting of alphanumerical characters

    Returns:
        str: Generated password
    """
    letters_and_digits = string.ascii_letters + string.digits
    return "".join(random.sample(letters_and_digits, DAEPLOY_REQUIRED_PASSWORD_LENGTH))


def create_token(dikt: dict, secret: str, expires_in: datetime.timedelta = None) -> str:
    """Creates a JSON Web Token with content 'dikt' using 'secret'. The
    token can optionally be configured to expire in a certain time using 'expire_in'.

    Args:
        dikt (dict): Additional payload to be added to token.
        secret (str): Secret used for signing the token.
        expires_in (datetime.timedelta, optional): Time in which token expires.
            Defaults to None.

    Returns:
        str: Token.
    """
    now = datetime.datetime.utcnow()

    mandatory_payload = {
        "iat": now,
    }

    if expires_in:
        mandatory_payload["exp"] = now + expires_in

    payload = {**dikt, **mandatory_payload}

    LOGGER.info(f"Creating JWT with payload: {payload}")

    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(auth_token: str, secret: str) -> Union[dict, bool]:
    """Verify a token 'auth_token' using signing key 'secret'

    Args:
        auth_token (str): Token to be verified
        secret (str): Secret used for signing the token

    Returns:
        Union[dict, bool]: Payload of token (dict) if successful verification
            otherwise bool.
    """
    LOGGER.debug(f"Veryfing token: {auth_token}")

    try:
        payload = jwt.decode(auth_token, secret, algorithms=["HS256", "RS256"])
        LOGGER.debug(f"Succesfully decoded token with payload: {payload}")
        return payload

    except jwt.ExpiredSignatureError:
        # Token has expired, ask user to log in again
        LOGGER.info(f"Token has expired: {auth_token}")
        return False

    except jwt.InvalidTokenError:
        # Invalid token! User must login!
        LOGGER.info(f"Token not valid: {auth_token}")
        return False


# Login handling
@ROUTER.get("/login", response_class=HTMLResponse, include_in_schema=False)
def show_login_page(request: Request, destination: Optional[str] = "/"):
    """Show login page

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    return TEMPLATES.TemplateResponse(
        "login.html",
        {"request": request, "ACTION": f"/auth/login?destination={destination}"},
        status_code=401,
    )


@ROUTER.post("/login", include_in_schema=False)
def login_user(
    username: str = Form(...),
    password: SecretStr = Form(...),
    destination: Optional[str] = "/",
):
    """Login user using 'username' and 'password' provided through form data.
    Sets a session cookie with a JWT in the response.

    \f
    # noqa: DAR101,DAR201,DAR401
    """

    LOGGER.info(f"Logging in user: {username}")

    # Fetch user from "DB" and validate password
    try:
        record = auth_db.get_user_record(username)
    except DatabaseNoMatchException:
        LOGGER.exception(f"User {username} failed to login!")
        return RedirectResponse(url=destination, status_code=303)

    if not bcrypt.checkpw(password.get_secret_value().encode(), record.password):
        return RedirectResponse(url=destination, status_code=303)

    # Construct token
    expire_in = datetime.timedelta(days=7)
    token = create_token(
        {
            "id": username,
        },
        config_db.get_jwt_token_secret(),
        expire_in,
    )

    # Add token to cookie and set to response
    response = RedirectResponse(url=destination, status_code=303)
    response.set_cookie("daeploy", token)

    return response


@ROUTER.get("/logout", include_in_schema=False)
def logout_user():
    """Log out the user (only works with cookies)

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    # Add token to cookie and set to response
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("daeploy", None)
    return response


# Verification endpoint, to be exposed to Traefik
@ROUTER.get("/verify", include_in_schema=False)
def verify_request(
    daeploy: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    x_forwarded_uri: Optional[str] = Header("/"),
):
    """Verify request using token from either cookie or Authorization header.

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    if not auth_enabled():
        # Allow all requests if auth is not enabled
        return "OK"

    # Check if we can find token in either cookie or header, prefer the cookie
    is_cookie = True  # True if token is fetched from the cookie
    token = daeploy

    # If token (from cookie) is empty and we have an Authorization token in the header
    if not token and authorization and "Bearer" in authorization:
        is_cookie = False  # Token no longer fetched from the cookie
        token = authorization.replace("Bearer ", "")

    # Try to verify the token
    payload = verify_token(token, config_db.get_jwt_token_secret())

    if not payload:
        # If we fetched token from a cookie, assuming the user is sitting at a
        # browser, lets redirect the user to the login page
        if is_cookie:
            return RedirectResponse(
                url=f"{get_external_proxy_url()}/auth/login"
                f"?destination={x_forwarded_uri}",
                status_code=303,
            )

        # Else we fetched the token from an Auth header and, assuming use from a
        # non-GUI application, lets raise a proper error
        raise HTTPException(401, detail="Token not valid!")

    if payload.get("exp") is None:
        # Long-lived API token, make sure it hasnt been removed from the db i.e.
        # is no longer valid
        try:
            auth_db.get_token_record(payload.get("id"))
        except DatabaseNoMatchException:
            raise HTTPException(401, detail="This API token is no longer valid!")

    return "OK"


# API token handling #
@ROUTER.get("/token", include_in_schema=False)
def list_api_tokens() -> List[UUID]:
    """List existing token uuids (not the tokens itself)

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    return [record.uuid for record in auth_db.get_all_token_records()]


@ROUTER.post("/token", include_in_schema=False, response_model=TokenResponse)
def new_api_token(expire_in_days: Optional[int] = None) -> dict:
    """ ""Generates new long-lived or semi-long-lived API token""

    Args:
        expire_in_days (int, optional): Number of days the token should be valid.
            Default to None, which corresponds to a long-lived token.

    \f
    # noqa: DAR101,DAR201,DAR401
    """

    uuid = uuid4()
    token = create_token(
        {
            "id": str(uuid),
        },
        config_db.get_jwt_token_secret(),
        expires_in=datetime.timedelta(expire_in_days) if expire_in_days else None,
    )

    auth_db.add_token_record(uuid)

    return {"Token": token, "Id": uuid}


@ROUTER.delete("/token", include_in_schema=False)
def delete_token(uuid: UUID):
    """Deletes long-lived API token with id 'uuid'

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    try:
        auth_db.delete_token_record(uuid)
    except DatabaseNoMatchException:
        raise HTTPException(410, detail="No such token to revoke!")

    return "OK"
