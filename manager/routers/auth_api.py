import logging
import datetime
from uuid import uuid4, UUID
from typing import Optional, List
from typing_extensions import TypedDict  # For compatability with python < 3.8

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
)
from manager.database import auth_db, config_db
from manager.exceptions import AuthError, DatabaseNoMatchException

ROUTER = APIRouter()

LOGGER = logging.getLogger(__name__)

TEMPLATES = Jinja2Templates(directory="manager/templates")


class TokenPayloadInput(TypedDict):
    id: str  # User ID


class TokenPayload(TokenPayloadInput):
    iat: int  # Token creating timestamp
    exp: int  # Token expiration timestamp


def create_token(
    payload: TokenPayloadInput, secret: str, expires_in: datetime.timedelta = None
) -> str:
    """Creates a JSON Web Token with content 'dikt' using 'secret'. The
    token can optionally be configured to expire in a certain time using 'expire_in'.

    Args:
        payload (TokenPayloadInput): Additional payload to be added to token.
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

    payload = {**payload, **mandatory_payload}

    LOGGER.info(f"Creating JWT with payload: {payload}")

    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(auth_token: str, secret: str) -> TokenPayload:
    """Verify a token 'auth_token' using signing key 'secret'

    Args:
        auth_token (str): Token to be verified
        secret (str): Secret used for signing the token

    Raises:
        AuthError: If token cannot be verified

    Returns:
        TokenPayload: Payload of token (dict) if successful verification
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
        raise AuthError("Expired token")

    except jwt.InvalidTokenError:
        # Invalid token! User must login!
        LOGGER.info(f"Token not valid: {auth_token}")
        raise AuthError("Invalid token")


def select_cookie_or_header(cookie: str, header: str) -> str:
    if cookie:
        return cookie
    if header:
        return header.replace("Bearer ", "")
    return ""


# Login handling
@ROUTER.get("/login", response_class=HTMLResponse)
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


@ROUTER.post("/login")
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


@ROUTER.get("/logout")
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
@ROUTER.get("/verify")
def verify_request(
    daeploy: Optional[str] = Cookie(None),
    authorization: Optional[str] = Header(None),
    x_forwarded_uri: Optional[str] = Header("/"),
):
    """Verify request using token from either cookie or Authorization header.

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    # Allow all requests if auth is not enabled
    if not auth_enabled():
        return "OK"

    # If token (from cookie) is empty and we have an Authorization token in the header
    is_cookie = True
    if not daeploy and authorization and "Bearer" in authorization:
        is_cookie = False

    token = select_cookie_or_header(daeploy, authorization)

    # Try to verify the token
    try:
        payload = verify_token(token, config_db.get_jwt_token_secret())
    except AuthError:
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
@ROUTER.get("/token")
def list_api_tokens() -> List[UUID]:
    """List existing token uuids (not the tokens itself)

    \f
    # noqa: DAR101,DAR201,DAR401
    """
    return [record.uuid for record in auth_db.get_all_token_records()]


@ROUTER.post("/token", response_model=TokenResponse)
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


@ROUTER.delete("/token")
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
