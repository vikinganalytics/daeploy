from fastapi import Cookie, Header, HTTPException, status, Depends

from manager.database.config_db import get_jwt_token_secret
from manager.routers.auth_api import select_cookie_or_header, verify_token
from manager.database import auth_db


def ensure_admin(daeploy: str = Cookie(None), authorization: str = Header(None)):
    token = select_cookie_or_header(daeploy, authorization)
    payload = verify_token(token, get_jwt_token_secret())
    if payload["id"] != "admin":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="This endpoint requires admin privileges",
        )
