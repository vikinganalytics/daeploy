"""
In pytest, the conftest.py file contains globally available fixture.
Gradually move fixtures that are used in multiple test modules into this file
"""

import os
import pytest
from fastapi.testclient import TestClient

from manager.app import app
from manager.database.database import initialize_db, remove_db


@pytest.fixture
def test_client():
    client = TestClient(app)
    try:
        client.cookies.clear()
        yield client
    finally:
        client.cookies.clear()


@pytest.fixture
def auth_enabled():
    os.environ["DAEPLOY_AUTH_ENABLED"] = "true"
    try:
        yield
    finally:
        del os.environ["DAEPLOY_AUTH_ENABLED"]


@pytest.fixture
def database():
    try:
        initialize_db()
        yield
    finally:
        remove_db()


@pytest.fixture
def test_client_logged_in(test_client: TestClient, auth_enabled, database):
    response = test_client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"},
        allow_redirects=False,
    )
    # Check that we have access!
    response = test_client.get("/auth/verify", allow_redirects=False)
    assert response.status_code == 200
    yield test_client
    # Logs out when removing cookies in parent fixture
