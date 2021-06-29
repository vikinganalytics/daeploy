import asyncio
import datetime
import json
import logging
import os
import time
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pydantic
import pytest
import logging
from fastapi.exceptions import FastAPIError
from fastapi.testclient import TestClient
from daeploy._service import db
from daeploy._service.service import _Service
from daeploy.communication import Severity, call_service, notify
from daeploy.data_types import ArrayInput, ArrayOutput, DataFrameInput, DataFrameOutput
from daeploy.utilities import get_db_table_limit


@pytest.fixture
def database():
    try:
        db.initialize_db()
        yield
    except Exception as e:
        print(e)
    finally:
        db.remove_db()


@pytest.fixture
def db_limit_fixture():
    try:
        default_limit, default_unit = get_db_table_limit()
        yield
    finally:
        os.environ["DAEPLOY_SERVICE_DB_TABLE_LIMIT"] = str(default_limit) + default_unit


@pytest.fixture
def db_limit_rows(db_limit_fixture):
    os.environ["DAEPLOY_SERVICE_DB_TABLE_LIMIT"] = "10rows"


@pytest.fixture
def db_limit_second(db_limit_fixture):
    os.environ["DAEPLOY_SERVICE_DB_TABLE_LIMIT"] = "1seconds"


@pytest.fixture
def db_limit_invalid_limit(db_limit_fixture):
    os.environ["DAEPLOY_SERVICE_DB_TABLE_LIMIT"] = "abcseconds"


@pytest.fixture
def db_limit_invalid_unit(db_limit_fixture):
    os.environ["DAEPLOY_SERVICE_DB_TABLE_LIMIT"] = "10avocados"


def valid_entrypoint_method_no_args():
    return 10


def valid_entrypoint_method_args(name: str, age: int) -> str:
    return "hello"


def invalid_entrypoint_return_type(name: str, age: int) -> np.int64:
    return 10


def invalid_entrypoint_argument_type(arg: np.int64) -> int:
    return 10


def entrypoint_with_request_argument(request: str) -> int:
    return 10


def entrypoint_with_arrays(arr1: ArrayInput, arr2: ArrayInput) -> ArrayOutput:
    return arr1 + arr2


def entrypoint_with_dataframes(
    df1: DataFrameInput, df2: DataFrameInput
) -> DataFrameOutput:
    return df1 + df2


def test_valid_entrypoint():
    service = _Service()
    service.entrypoint(valid_entrypoint_method_no_args)
    method_route = "/valid_entrypoint_method_no_args"
    routes = [route.path for route in service.app.routes]
    assert method_route in routes


def test_valid_entrypoint_kwargs():
    service = _Service()
    service.entrypoint(response_model=int)(valid_entrypoint_method_no_args)
    method_route = "/valid_entrypoint_method_no_args"
    routes = [route.path for route in service.app.routes]
    assert method_route in routes


def test_valid_entrypoint_with_args():
    service = _Service()
    service.entrypoint(valid_entrypoint_method_args)
    method_route = "/valid_entrypoint_method_args"
    routes = [route.path for route in service.app.routes]
    assert method_route in routes


def test_valid_entrypoint_with_args_kwargs():
    service = _Service()
    service.entrypoint(status_code=222)(valid_entrypoint_method_args)
    method_route = "/valid_entrypoint_method_args"
    routes = [route.path for route in service.app.routes]
    assert method_route in routes


def test_invalid_entrypoint_invalid_return_type():
    service = _Service()
    with pytest.raises(FastAPIError):
        service.entrypoint()(invalid_entrypoint_return_type)


def test_invalid_entrypoint_invalid_argument_type():
    service = _Service()
    with pytest.raises(FastAPIError):
        service.entrypoint()(invalid_entrypoint_argument_type)


def test_using_request_argument_in_entrypoint():
    service = _Service()
    service.entrypoint(entrypoint_with_request_argument)


def test_array_types():
    service = _Service()
    entrypoint = service.entrypoint(entrypoint_with_arrays)
    client = TestClient(service.app)

    arr1 = np.array([1, 2, 3, 4, 5])
    arr2 = np.array([6, 7, 8, 9, 10])
    inputs = {"arr1": arr1.tolist(), "arr2": arr2.tolist()}
    response = client.post(
        "/entrypoint_with_arrays",
        json=inputs,
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    arr_result = entrypoint(arr1, arr2)
    assert isinstance(arr_result, np.ndarray)
    assert response.json() == arr_result.tolist()


def test_df_types():
    service = _Service()
    entrypoint = service.entrypoint(entrypoint_with_dataframes)
    client = TestClient(service.app)

    df1 = pd.DataFrame.from_dict({"col1": [1, 2, 3, 4, 5]})
    df2 = pd.DataFrame.from_dict({"col1": [6, 7, 8, 9, 10]})

    inputs = {"df1": df1.to_dict(), "df2": df2.to_dict()}
    response = client.post(
        "/entrypoint_with_dataframes",
        json=inputs,
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    # response.json() is dict in json format and df.to_json is json string
    df_result = entrypoint(df1, df2)
    assert isinstance(df_result, pd.DataFrame)
    assert response.json() == json.loads(df_result.to_json())


def test_entrypoint_function_validation():
    service = _Service()
    entrypoint = service.entrypoint(valid_entrypoint_method_args)
    entrypoint("name", 123)  # Correct types
    with pytest.raises(pydantic.ValidationError):
        entrypoint(123, "name")  # Wrong types


def test_daeploy_service_init():
    service = _Service()
    parameters_route = "/~parameters"
    routes = [route.path for route in service.app.routes]
    assert parameters_route in routes


def test_get_all_parameters():
    service = _Service()
    service.parameters["key"] = {"value": 10}
    service.parameters["key2"] = {"value": 20}

    with TestClient(service.app) as client:
        response = client.get("/~parameters", headers={"accept": "application/json"})

    assert response.json() == {"key": 10, "key2": 20}


def test_get_parameter_by_code():
    service = _Service()
    service.parameters["key"] = {"value": 10}
    service.parameters["key2"] = {"value": 20}
    assert service.get_parameter("key") == 10


def test_get_paramter_by_api():
    service = _Service()
    service.add_parameter("myparameter", 10)

    with TestClient(service.app) as client:

        response = client.get(
            "/~parameters/myparameter", headers={"accept": "application/json"}
        )

    assert response.status_code == 200
    assert response.json() == 10


def test_add_parameter():
    service = _Service()
    service.add_parameter("myparameter", value=10)
    my_parameter_route = "/~parameters/myparameter"
    routes = [route.path for route in service.app.routes]
    assert my_parameter_route in routes


def test_update_parameter_not_registered_parameter():
    service = _Service()
    service.add_parameter("myparameter", 10)

    with TestClient(service.app) as client:
        response = client.post("/~parameters/myparameter2", json={"value": 1000})

    assert response.status_code == 404


def test_update_parameter():
    service = _Service()
    service.add_parameter("myparameter", 10)

    with TestClient(service.app) as client:

        req = {"value": 1000}

        response = client.post(
            "/~parameters/myparameter", json=req, headers={"accept": "application/json"}
        )

    assert response.status_code == 200


def test_internal_parameter():
    service = _Service()
    service.add_parameter("myparameter", 10, expose=False)

    with TestClient(service.app) as client:

        req = {"value": 1000}

        response = client.post(
            "/~parameters/myparameter", json=req, headers={"accept": "application/json"}
        )

    assert response.status_code == 405


def test_set_parameter():
    service = _Service()
    service.add_parameter("myparameter", 10)
    service.set_parameter("myparameter", 20)

    with TestClient(service.app) as client:

        response = client.get(
            "/~parameters/myparameter", headers={"accept": "application/json"}
        )
        assert response.json() == 20


def test_set_nonexisting_parameter():
    service = _Service()
    service.add_parameter("myparameter", 10)
    with pytest.raises(KeyError):
        service.set_parameter("nonexistent", 20)


def test_set_wrong_type():
    service = _Service()
    service.add_parameter("myparameter", 10)
    service.set_parameter("myparameter", "20")
    assert service.get_parameter("myparameter") == 20


def test_int_to_float():
    service = _Service()
    service.add_parameter("myparameter", 10)
    assert isinstance(service.get_parameter("myparameter"), float)
    service.set_parameter("myparameter", 20)
    assert isinstance(service.get_parameter("myparameter"), float)


def test_set_list():
    service = _Service()
    service.add_parameter("myparameter", [1, 2, 3, 4])
    service.set_parameter("myparameter", [3, 2, 1])


@patch("daeploy.communication.request")
def test_notify(request):
    datetime_mock = Mock(wraps=datetime.datetime)
    datetime_mock.utcnow.return_value = datetime.datetime(1999, 1, 1)

    with patch("datetime.datetime", new=datetime_mock):
        notify(
            msg="Oh, I'm the msg.",
            severity=Severity.WARNING,
            emails=["mvi.email.test@gmail.com"],
        )

        expected_url = "http://host.docker.internal/notifications/"
        auth_domains = ["localhost"]
        expected_headers = {
            "Authorization": "Bearer unknown",
            "Content-Type": "application/json",
            "Host": "localhost",
        }
        expexted_payload = {
            "service_name": "unknown",
            "service_version": "0.0.0",
            "msg": "Oh, I'm the msg.",
            "severity": 1,
            "dashboard": True,
            "emails": ["mvi.email.test@gmail.com"],
            "timer": 0,
            "timestamp": str(datetime.datetime.utcnow()),
        }

        request.assert_called_with(
            "POST",
            expected_url,
            auth_domains=auth_domains,
            headers=expected_headers,
            json=expexted_payload,
        )


@patch("daeploy.communication.request")
def test_notify_negative_time(request):
    datetime_mock = Mock(wraps=datetime.datetime)
    datetime_mock.utcnow.return_value = datetime.datetime(1999, 1, 1)

    with patch("datetime.datetime", new=datetime_mock):
        notify(
            msg="Oh, I'm the msg.",
            severity=Severity.WARNING,
            timer=-10,
        )

        expected_url = "http://host.docker.internal/notifications/"
        auth_domains = ["localhost"]
        expected_headers = {
            "Authorization": "Bearer unknown",
            "Content-Type": "application/json",
            "Host": "localhost",
        }
        expexted_payload = {
            "service_name": "unknown",
            "service_version": "0.0.0",
            "msg": "Oh, I'm the msg.",
            "severity": 1,
            "dashboard": True,
            "emails": None,
            "timer": 0,
            "timestamp": str(datetime.datetime.utcnow()),
        }

        request.assert_called_with(
            "POST",
            expected_url,
            auth_domains=auth_domains,
            headers=expected_headers,
            json=expexted_payload,
        )


@patch("daeploy.communication.request")
def test_call_service_wihtout_service_version(request):
    service_name = "myservice"
    entrypoint_name = "mymethod"
    arguments = {"value": 10, "active": False}

    call_service(
        service_name=service_name, entrypoint_name=entrypoint_name, arguments=arguments
    )

    expected_url = (
        f"http://host.docker.internal/services/{service_name}/{entrypoint_name}"
    )
    auth_domains = ["localhost"]
    expected_headers = {
        "Authorization": "Bearer unknown",
        "Content-Type": "application/json",
        "Host": "localhost",
    }

    request.assert_called_with(
        "POST",
        url=expected_url,
        auth_domains=auth_domains,
        headers=expected_headers,
        json=arguments,
    )


@patch("daeploy.communication.request")
def test_call_service_with_service_version(request):
    service_name = "myservice"
    entrypoint_name = "mymethod"
    arguments = {"value": 10, "active": False}
    version = "0.0.4"

    call_service(
        service_name=service_name,
        entrypoint_name=entrypoint_name,
        arguments=arguments,
        service_version=version,
    )

    expected_url = f"http://host.docker.internal/services/{service_name}_{version}/{entrypoint_name}"
    auth_domains = ["localhost"]
    expected_headers = {
        "Authorization": "Bearer unknown",
        "Content-Type": "application/json",
        "Host": "localhost",
    }

    request.assert_called_with(
        "POST",
        url=expected_url,
        auth_domains=auth_domains,
        headers=expected_headers,
        json=arguments,
    )


@patch("daeploy.communication.request")
def test_call_service_log_args(request, caplog):
    service_name = "myservice"
    entrypoint_name = "mymethod"
    arguments = {"value": 10, "active": False}
    version = "0.0.4"
    with caplog.at_level(logging.INFO, logger="daeploy.communication"):
        call_service(
            service_name=service_name,
            entrypoint_name=entrypoint_name,
            arguments=arguments,
            service_version=version,
        )
        assert f"{arguments}" not in caplog.text

    with caplog.at_level(logging.DEBUG, logger="daeploy.communication"):
        call_service(
            service_name=service_name,
            entrypoint_name=entrypoint_name,
            arguments=arguments,
            service_version=version,
        )
        assert f"{arguments}" in caplog.text


@patch("daeploy.communication.request")
def test_call_service_invalid_method(request):
    service_name = "myservice"
    entrypoint_name = "mymethod"
    arguments = {"value": 10, "active": False}
    version = "1.0.0"

    with pytest.raises(ValueError):
        call_service(
            service_name=service_name,
            entrypoint_name=entrypoint_name,
            service_version=version,
            arguments=arguments,
            entrypoint_method="NOT A HTTP METHOD",
        )


def test_local_invocation_pydantic_validation():
    service = _Service()
    wrapped = service.entrypoint(valid_entrypoint_method_args)

    assert valid_entrypoint_method_args(32, "Urban") == "hello"  # Args of wrong type!

    with pytest.raises(pydantic.error_wrappers.ValidationError):
        wrapped(32, "Urban")

    assert wrapped("Urban", 32) == "hello"


def test_store_calls_to_database(database):
    service = _Service()
    service.store(my_oh_my=10)
    # Needed grace period
    time.sleep(0.1)
    assert db.stored_variables() == ["my_oh_my"]
    assert len(db.read_from_ts(name="my_oh_my")) == 1


def test_invalid_dtype_to_database_to_str(database):
    service = _Service()
    service.store(my_oh_my=list())
    time.sleep(0.1)
    # Since list as dtype it should be converted to string
    records = db.read_from_ts(name="my_oh_my")
    assert records[0].value == str(list())


def test_update_parameter_monitored(database):
    service = _Service()
    service.add_parameter("myparameter", 10, monitor=True)
    time.sleep(0.1)
    assert len(db.read_from_ts(name="myparameter")) == 1
    client = TestClient(service.app)

    req = {"value": 1000}
    response = client.post(
        "/~parameters/myparameter", json=req, headers={"accept": "application/json"}
    )
    time.sleep(0.1)
    assert len(db.read_from_ts(name="myparameter")) == 2

    assert response.status_code == 200


def test_entrypoint_monitored(database):
    service = _Service()
    service.entrypoint(monitor=True)(valid_entrypoint_method_args)
    client = TestClient(service.app)

    req = {"name": "Rune", "age": 100}
    response = client.post(
        "/valid_entrypoint_method_args",
        json=req,
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    time.sleep(0.5)
    print(db.stored_variables())
    assert db.stored_variables() == [
        "valid_entrypoint_method_args_request",
        "valid_entrypoint_method_args_response",
    ]


def test_entrypoint_not_monitored():
    service = _Service()
    service.store = MagicMock()
    service.entrypoint(monitor=False)(valid_entrypoint_method_args)
    client = TestClient(service.app)

    req = {"name": "Rune", "age": 100}
    response = client.post(
        "/valid_entrypoint_method_args",
        json=req,
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    service.store.assert_not_called()


def test_entrypoint_get():
    service = _Service()
    service.entrypoint(monitor=False, method="GET")(valid_entrypoint_method_args)
    client = TestClient(service.app)

    req = {"name": "Rune", "age": 100}
    response = client.get(
        "/valid_entrypoint_method_args",
        json=req,
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200


def test_entrypoint_invalid_method():
    service = _Service()
    with pytest.raises(ValueError):
        service.entrypoint(monitor=False, method="NOT A HTTP METHOD")(
            valid_entrypoint_method_args
        )


@patch("daeploy.communication.request")
def test_call_service_get_entrypoint(request):
    service_name = "myservice"
    entrypoint_name = "mymethod"
    version = "1.0.0"
    arguments = {"value": 10, "active": False}

    call_service(
        service_name=service_name,
        entrypoint_name=entrypoint_name,
        arguments=arguments,
        service_version=version,
        entrypoint_method="GET",
    )

    expected_url = f"http://host.docker.internal/services/{service_name}_{version}/{entrypoint_name}"
    auth_domains = ["localhost"]
    expected_headers = {
        "Authorization": "Bearer unknown",
        "Content-Type": "application/json",
        "Host": "localhost",
    }

    request.assert_called_with(
        "GET",
        url=expected_url,
        auth_domains=auth_domains,
        headers=expected_headers,
        json=arguments,
    )


def test_call_every_decorator():
    service = _Service()

    mock1 = Mock()
    mock2 = Mock()

    # Decorate with `call_every` decorator and check that it returns the
    # unwrapped function
    assert mock1 == service.call_every(seconds=0.1, wait_first=False)(mock1)
    assert mock2 == service.call_every(seconds=0.1, wait_first=True)(mock2)

    # Use asyncio.sleep to let the tasks run appropriately in a test env
    with TestClient(service.app) as client:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.sleep(1))

    # At 0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 seconds = 10 calls
    assert mock1.call_count == 10

    # At 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9 seconds = 9 calls
    assert mock2.call_count == 9


def test_call_every_decorator_long_execution_time():
    service = _Service()

    # Long running func with shorter execution interval
    @service.call_every(seconds=0.1)
    def long_running_func():
        time.sleep(0.5)

    # Check that warnings are emitted
    with pytest.warns(UserWarning):
        # Use asyncio.sleep to let the tasks run appropriately in a test env
        with TestClient(service.app) as client:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(asyncio.sleep(1))


def test_database_table_creation(database):

    timestamp = datetime.datetime.utcnow()
    db.write_to_ts("float", 1.0, timestamp)
    db.write_to_ts("text", "1", timestamp)
    db.write_to_ts("dict", {"a": 4}, timestamp)
    db.write_to_ts("list", {"a": 4}, timestamp)
    # Make sure the writer thread has time to process everything
    time.sleep(0.2)

    assert db.stored_variables() == ["float", "text", "dict", "list"]

    db.write_to_ts("invalid", lambda x: x, datetime.datetime.utcnow())
    time.sleep(0.2)
    assert "invalid" not in db.stored_variables()


def test_jsonable_type_db(database):

    timestamp = datetime.datetime.utcnow()
    db.write_to_ts("dict", {"a": 4}, timestamp)
    time.sleep(0.2)

    assert db.read_from_ts("dict")[-1].value == json.dumps({"a": 4})


def test_continuous_storing_of_and_reading_of_variables(database):

    for i in range(200):
        timestamp = datetime.datetime.utcnow()
        db.write_to_ts("float", float(i), timestamp)
        db.write_to_ts("text", str(i), timestamp)
        time.sleep(0.02)

    time.sleep(1)

    assert len(db.read_from_ts("float")) == 200
    assert len(db.read_from_ts("text")) == 200

    assert db.read_from_ts("float")[-1].value == 199.0
    assert db.read_from_ts("text")[-1].value == "199"


def test_edge_case_type_storing(database):
    timestamp = datetime.datetime.utcnow()

    db.write_to_ts("my_bool", float(True), timestamp)
    db.write_to_ts("my_stringified_int", "10", timestamp)
    db.write_to_ts("my_stringified_float", "12.0", timestamp)
    db.write_to_ts("my_normal_float", 10.10, timestamp)
    db.write_to_ts("my.normal.float", 10.10, timestamp)

    time.sleep(1)

    assert db.read_from_ts("my_bool")[-1].value == 1.0
    assert db.read_from_ts("my_stringified_int")[-1].value == "10"
    assert db.read_from_ts("my_stringified_float")[-1].value == "12.0"
    assert db.read_from_ts("my_normal_float")[-1].value == 10.10
    assert db.read_from_ts("my.normal.float")[-1].value == 10.10


def test_read_timerange(database):

    before = datetime.datetime.utcnow()
    mid = None

    for i in range(200):
        db.write_to_ts("float", float(i), datetime.datetime.utcnow())
        time.sleep(0.01)
        if i == 100:
            mid = datetime.datetime.utcnow()

    time.sleep(1)

    after = datetime.datetime.utcnow()

    # Check that default values behave according to expectations
    assert (
        len(db.read_from_ts("float", from_time=before, to_time=after))
        == len(db.read_from_ts("float", to_time=after))
        == len(db.read_from_ts("float", from_time=before))
        == 200
    )

    assert len(db.read_from_ts("float", from_time=before, to_time=mid)) < 200


def test_database_limit_rows(database, db_limit_rows):
    before = datetime.datetime.utcnow()
    for i in range(12):
        db.write_to_ts("float", float(i), datetime.datetime.utcnow())
        time.sleep(0.01)
        if i == 1:
            mid = datetime.datetime.utcnow()

    db.clean_database()

    assert len(db.read_from_ts("float")) == 10
    assert len(db.read_from_ts("float", from_time=before, to_time=mid)) == 0


def test_database_limit_time(database, db_limit_second):
    before = datetime.datetime.utcnow()
    for i in range(2):
        db.write_to_ts("float", float(i), datetime.datetime.utcnow())
        time.sleep(0.6)

    db.clean_database()

    values = db.read_from_ts("float")
    assert len(values) == 1
    assert values[0].value == 1


def test_database_limit_invalid_limit(database, db_limit_invalid_limit):
    limit, limiter = get_db_table_limit()
    assert limit == 90
    assert limiter == "days"


def test_database_limit_invalid_unit(database, db_limit_invalid_unit):
    limit, limiter = get_db_table_limit()
    assert limit == 90
    assert limiter == "days"
