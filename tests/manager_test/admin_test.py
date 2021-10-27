from fastapi.testclient import TestClient
from fastapi import status

TOKEN = "abc"
USERNAME = "user"
PASSWORD = "password"


def add_user(client, username, password, headers=None):
    return client.post(
        f"/admin/user/{username}",
        json={"password": password},
        headers=headers,
    )


def list_users(client, headers=None):
    return client.get("/admin/user", headers=headers)


def delete_user(client, username, headers=None):
    return client.delete(
        f"/admin/user/{username}",
        headers=headers,
    )


def update_password(client, username, new_password, headers=None):
    return client.put(
        f"/admin/user/{username}",
        json={"password": new_password},
        headers=headers,
    )


def change_user(client, username, password):
    add_user(client, username, password)
    client.post(
        "/auth/login",
        data={"username": username, "password": password},
        allow_redirects=False,
    )


# Add user


def test_add_user(test_client_logged_in: TestClient):
    res = add_user(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_201_CREATED


def test_add_user_conflict(test_client_logged_in: TestClient):
    res = add_user(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_201_CREATED
    res = add_user(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_409_CONFLICT


def test_add_user_invalid_token(test_client: TestClient, auth_enabled, database):
    res = add_user(test_client, USERNAME, PASSWORD)
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid token"


def test_add_user_not_admin(test_client_logged_in: TestClient):
    change_user(test_client_logged_in, USERNAME, PASSWORD)
    res = add_user(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "This endpoint requires admin privileges"


# List user


def test_list_users(test_client_logged_in: TestClient):
    res = list_users(test_client_logged_in)
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == ["admin"]

    add_user(test_client_logged_in, USERNAME, PASSWORD)
    res = list_users(test_client_logged_in)
    assert res.status_code == status.HTTP_200_OK
    assert res.json() == ["admin", USERNAME]


def test_list_users_invalid_token(test_client: TestClient, auth_enabled, database):
    res = list_users(test_client)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["detail"] == "Invalid token"


def test_list_users_not_admin(test_client_logged_in: TestClient):
    change_user(test_client_logged_in, USERNAME, PASSWORD)
    res = list_users(test_client_logged_in)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "This endpoint requires admin privileges"


# Delete user


def test_delete_user(test_client_logged_in: TestClient):
    add_user(test_client_logged_in, USERNAME, PASSWORD)
    res = delete_user(test_client_logged_in, USERNAME)
    assert res.status_code == status.HTTP_200_OK


def test_delete_user_not_found(test_client_logged_in: TestClient):
    res = delete_user(test_client_logged_in, USERNAME)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_delete_admin(test_client_logged_in: TestClient):
    res = delete_user(test_client_logged_in, "admin")
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "Modifications on admin user not allowed"


def test_delete_user_invalid_token(test_client, auth_enabled, database):
    res = delete_user(test_client, USERNAME)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["detail"] == "Invalid token"


def test_delete_user_not_admin(test_client_logged_in: TestClient):
    change_user(test_client_logged_in, USERNAME, PASSWORD)
    res = delete_user(test_client_logged_in, USERNAME)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "This endpoint requires admin privileges"


# Update password


def test_update_password(test_client_logged_in: TestClient):
    add_user(test_client_logged_in, USERNAME, PASSWORD)
    res = update_password(test_client_logged_in, USERNAME, "new_password")
    assert res.status_code == status.HTTP_200_OK


def test_update_password_not_found(test_client_logged_in: TestClient):
    res = update_password(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_update_password_admin(test_client_logged_in: TestClient):
    res = update_password(test_client_logged_in, "admin", PASSWORD)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "Modifications on admin user not allowed"


def test_update_password_invalid_token(test_client, auth_enabled, database):
    res = update_password(test_client, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_401_UNAUTHORIZED
    assert res.json()["detail"] == "Invalid token"


def test_update_password_not_admin(test_client_logged_in: TestClient):
    change_user(test_client_logged_in, USERNAME, PASSWORD)
    res = update_password(test_client_logged_in, USERNAME, PASSWORD)
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert res.json()["detail"] == "This endpoint requires admin privileges"
