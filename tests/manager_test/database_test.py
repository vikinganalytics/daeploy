from copy import copy
from uuid import uuid4
from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from manager.database.database import (
    session_scope,
    Service,
)
from manager.database import service_db, auth_db, config_db
from manager.exceptions import (
    DatabaseConflictException,
    DatabaseOutOfSyncException,
    DatabaseNoMatchException,
)

myservice = ["myservice", "1.0.0", "myimage", "http://myurl.com", str(uuid4())]
myservice_dict = {
    "name": "myservice",
    "version": "1.0.0",
    "image": "myimage",
    "url": "http://myurl.com",
    "main": True,
}


def test_get_service_record(database):
    service = Service(**myservice_dict)

    with session_scope() as session:
        session.add(service)
        session.commit()

        return_service = service_db.get_service_record(
            session, myservice_dict["name"], myservice_dict["version"]
        )

    assert service == return_service


def test_get_service_record_without_match(database):
    with session_scope() as session:
        with pytest.raises(DatabaseNoMatchException):
            service_db.get_service_record(session, "nonexisting_service", "1.0.0")


def test_get_main_service(database):
    myservice2_dict = copy(myservice_dict)
    myservice2_dict["version"] = "2.0.0"
    myservice2_dict["main"] = False
    service = Service(**myservice_dict)
    service2 = Service(**myservice2_dict)

    with session_scope() as session:
        session.add(service)
        session.add(service2)
        session.commit()

        main_service = service_db.get_main_service_record(session, "myservice")

        assert main_service == service


def test_get_main_service_record_without_match(database):
    with session_scope() as session:
        with pytest.raises(DatabaseNoMatchException):
            service_db.get_main_service_record(session, "nonexisting_service")


def test_duplicate_service_in_db(database):
    service = Service(**myservice_dict)
    service2 = Service(**myservice_dict)

    with session_scope() as session:
        session.add(service)
        session.add(service2)

    with session_scope() as session:
        with pytest.raises(DatabaseConflictException):
            service_db.get_service_record(session, name="myservice", version="1.0.0")

        with pytest.raises(DatabaseConflictException):
            service_db.get_main_service_record(session, name="myservice")


def test_add_new_service_record_only_first_main(database):
    service_db.add_new_service_record(*myservice)

    myservice2 = copy(myservice)
    myservice2[1] = "2.0.0"
    service_db.add_new_service_record(*myservice2)

    main_version, shadow_versions = service_db.get_main_and_shadow_versions("myservice")

    assert main_version == "1.0.0"
    assert shadow_versions[0] == "2.0.0"


def test_add_new_service_record_identical_services(database):
    service_db.add_new_service_record(*myservice)

    with pytest.raises(DatabaseConflictException):
        service_db.add_new_service_record(*myservice)


def test_delete_service_record(database):
    service_db.add_new_service_record(*myservice)

    service_db.delete_service_record("myservice", "1.0.0")

    with session_scope() as session:
        services = session.query(Service).all()
    assert len(services) == 0


def test_delete_service_record_without_match(database):
    with pytest.raises(DatabaseNoMatchException):
        service_db.delete_service_record("nonexisting_service", "1.0.0")


def test_get_main_and_shadow_versions_no_match(database):
    main_version, shadow_version = service_db.get_main_and_shadow_versions("myservice")
    assert main_version is None
    assert shadow_version == []


def test_get_main_and_shadow_versions_no_main(database):
    myservice2 = copy(myservice_dict)
    myservice2["main"] = False
    service = Service(**myservice2)
    with session_scope() as session:
        session.add(service)

    main_version, shadow_versions = service_db.get_main_and_shadow_versions("myservice")
    assert main_version is None
    assert shadow_versions == ["1.0.0"]


def test_assign_main_version(database):
    service_db.add_new_service_record(*myservice)

    myservice2 = copy(myservice)
    myservice2[1] = "2.0.0"
    service_db.add_new_service_record(*myservice2)

    main_version, shadow_versions = service_db.get_main_and_shadow_versions("myservice")
    assert main_version == "1.0.0"
    assert shadow_versions[0] == "2.0.0"

    service_db.assign_main_version("myservice", "2.0.0")
    main_version, shadow_versions = service_db.get_main_and_shadow_versions("myservice")

    assert main_version == "2.0.0"
    assert shadow_versions[0] == "1.0.0"


def test_assign_main_version_no_match(database):
    with pytest.raises(DatabaseNoMatchException):
        service_db.assign_main_version("myservice", "2.0.0")


def test_assign_main_version_main_to_main(database):
    service = Service(**myservice_dict)

    with session_scope() as session:
        session.add(service)

    main_version, _ = service_db.get_main_and_shadow_versions("myservice")
    assert main_version == "1.0.0"

    service_db.assign_main_version("myservice", "1.0.0")
    main_version, _ = service_db.get_main_and_shadow_versions("myservice")
    assert main_version == "1.0.0"


def test_runtime_db_out_of_sync_db_ahead(database):
    service = Service(**myservice_dict)

    with session_scope() as session:
        session.add(service)

    runtime_services = []
    db_services = service_db.get_all_services_db()
    with pytest.raises(DatabaseOutOfSyncException):
        service_db.compare_runtime_db(runtime_services, db_services)


def test_runtime_db_out_of_sync_rt_ahead(database):
    runtime_services = ["daeploy-myservice-1.0.0"]
    db_services = service_db.get_all_services_db()
    with pytest.raises(DatabaseOutOfSyncException):
        service_db.compare_runtime_db(runtime_services, db_services)


def test_config_db_add_and_retrieve_success(database):
    key, value = "KEY", "VALUE"
    config_db.add_config_record(key, value)
    record = config_db.get_config_record(key)
    assert record.value == value


def test_config_db_retrieve_non_existent(database):
    with pytest.raises(DatabaseNoMatchException):
        record = config_db.get_config_record("KEY")


def test_config_db_add_unique_violation(database):
    key, value = "KEY", "VALUE"
    config_db.add_config_record(key, value)

    with pytest.raises(IntegrityError):
        config_db.add_config_record(key, value)


def test_config_db_jwt_token_secret_get(database):
    # Set by default to a random value when starting the db
    assert config_db.get_jwt_token_secret() is not None


def test_config_db_jwt_token_secret_set_not_accepted(database):
    # Set by default to a random value when starting the db
    with pytest.warns(UserWarning):
        config_db.set_jwt_token_secret("SECRET")


def test_auth_db_get_default_user(database):
    record = auth_db.get_user_record("admin")
    assert record.name == "admin"


def test_auth_db_get_set_user(database):
    auth_db.add_user_record("user", "password")
    record = auth_db.get_user_record("user")
    assert record.name == "user"
    assert record.password != "password"  # Should be hashed!


def test_auth_db_add_existing_user(database):
    with pytest.raises(IntegrityError):
        auth_db.add_user_record("admin", "hallaballo")


def test_auth_db_get_non_existing_user(database):
    with pytest.raises(DatabaseNoMatchException):
        record = auth_db.get_user_record("user")


def test_auth_db_get_all_users(database):
    assert auth_db.get_all_users() == ["admin"]

    auth_db.add_user_record("user", "password")
    assert auth_db.get_all_users() == ["admin", "user"]


def test_auth_db_delete_user_record(database):
    auth_db.delete_user_record("admin")
    assert auth_db.get_all_users() == []


def test_auth_db_delete_non_existing_record(database):
    with pytest.raises(DatabaseNoMatchException):
        auth_db.delete_user_record("nope")


def test_auth_db_get_set_delete_token(database):
    uuid = uuid4()
    auth_db.add_token_record(uuid)
    record = auth_db.get_token_record(uuid)
    assert record is not None
    assert record.uuid == uuid
    assert isinstance(record.created_at, datetime)

    auth_db.delete_token_record(uuid)
    with pytest.raises(DatabaseNoMatchException):
        record = auth_db.get_token_record(uuid)

    with pytest.raises(DatabaseNoMatchException):
        auth_db.delete_token_record(uuid)


def test_auth_db_add_existing_token(database):
    uuid = uuid4()
    auth_db.add_token_record(uuid)
    with pytest.raises(IntegrityError):
        auth_db.add_token_record(uuid)


def test_auth_db_get_non_existing_token(database):
    with pytest.raises(DatabaseNoMatchException):
        record = auth_db.get_token_record(uuid4())


def test_auth_db_get_all_tokens(database):
    records = auth_db.get_all_token_records()
    assert records == []
