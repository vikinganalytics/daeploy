import logging
from typing import List

from fastapi import Cookie, Header, HTTPException, status, Depends, APIRouter
from sqlalchemy.exc import IntegrityError

from manager.database.config_db import get_jwt_token_secret
from manager.routers.auth_api import TokenPayload, select_cookie_or_header, verify_token
from manager.database import auth_db
from manager.data_models.request_models import UserRequest
from manager.exceptions import AuthError, DatabaseNoMatchException

ROUTER = APIRouter()
LOGGER = logging.getLogger(__name__)


def get_token_payload(
    daeploy: str = Cookie(None), authorization: str = Header(None)
) -> TokenPayload:
    token = select_cookie_or_header(daeploy, authorization)
    try:
        return verify_token(token, get_jwt_token_secret())
    except AuthError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=str(exc))


def ensure_admin(payload: TokenPayload) -> TokenPayload:
    if payload["id"] != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires admin privileges",
        )


@ROUTER.post("/user/{username}", status_code=status.HTTP_201_CREATED)
def add_user(
    username: str,
    user_request: UserRequest,
    payload: TokenPayload = Depends(get_token_payload),
):
    ensure_admin(payload)
    try:
        auth_db.add_user_record(username, user_request.password.get_secret_value())
    except IntegrityError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"User {username} already exists"
        )
    return "Created"


@ROUTER.get("/user", response_model=List[str])
def list_users(payload: TokenPayload = Depends(get_token_payload)) -> List[str]:
    ensure_admin(payload)
    users = auth_db.get_all_users()
    return users


@ROUTER.delete("/user/{username}")
def delete_user(username: str, payload: TokenPayload = Depends(get_token_payload)):
    ensure_admin(payload)
    if username == "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Modifications on admin user not allowed"
        )

    try:
        auth_db.delete_user_record(username)
    except DatabaseNoMatchException:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"User {username} not found"
        )
    return "OK"


@ROUTER.put("/user/{username}")
def update_password(
    username: str,
    user_request: UserRequest,
    payload: TokenPayload = Depends(get_token_payload),
):
    delete_user(username, payload)
    add_user(username, user_request, payload)
    return "OK"
