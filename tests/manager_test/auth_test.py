import pytest
from fastapi.testclient import TestClient

from manager.app import app

client = TestClient(app)


@pytest.fixture
def clear_cookies():
    try:
        client.cookies.clear()
        yield
    finally:
        client.cookies.clear()


@pytest.fixture
def exclude_middleware():
    # https://github.com/encode/starlette/issues/472
    user_middleware = app.user_middleware.copy()
    app.user_middleware = []
    app.middleware_stack = app.build_middleware_stack()
    yield
    app.user_middleware = user_middleware
    app.middleware_stack = app.build_middleware_stack()


def test_login_page(exclude_middleware):
    response = client.get("/auth/login")
    assert response.status_code == 401


def test_verification_without_auth(database):
    response = client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 200


def test_failed_login(database, auth_enabled):
    # Login
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrongpassword"},
        allow_redirects=False,
    )
    assert response.status_code == 303

    # No access after
    response = client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 303


def test_cookie_token(database, auth_enabled):
    # No access from beginning
    response = client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 303

    # Login
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"},
        allow_redirects=False,
    )
    assert response.status_code == 303

    # Check that we have access!
    response = client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 200

    # Logout
    response = client.get("/auth/logout", allow_redirects=False)
    assert response.status_code == 303

    # No access at the end
    response = client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 303


def test_API_token(clear_cookies, database, auth_enabled):
    # No access from beginning
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer mumbojumbo"},
        allow_redirects=True,
    )
    assert response.status_code == 401

    # Empty from the beginning
    response = client.get("/auth/token")
    assert response.status_code == 200
    assert response.json() == []

    # Get new token
    response = client.post("/auth/token")
    assert response.status_code == 200
    token_response = response.json()
    token = token_response["Token"]

    # Check that one token has been added to the DB
    response = client.get("/auth/token")
    assert response.status_code == 200
    uuids = response.json()
    assert len(uuids) == 1
    assert uuids[0] == token_response["Id"]

    # Use token to make sure we now have access, NOT allowing redirects
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=False,
    )
    assert response.status_code == 200

    # Use token to make sure we now have access, allowing redirects
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=True,
    )
    assert response.status_code == 200

    # Revoke token
    response = client.delete("/auth/token", params={"uuid": uuids[0]})
    assert response.status_code == 200

    # No access at the end
    response = client.get(
        "/auth/verify",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=True,
    )
    assert response.status_code == 401
