import json

import numpy as np
from fastapi.testclient import TestClient
import examples.typing.ndarray_service.service as ndarray_service
import examples.typing.row_sum_service.service as row_sum_service

app_ndarray = ndarray_service.service.app
client_ndarray = TestClient(app_ndarray)

app_row_sum = row_sum_service.service.app
client_row_sum = TestClient(app_row_sum)


def test_ndarray_service_api():
    test_data = json.dumps({"array1": [1, 2, 3], "array2": [4, 5, 6]})
    response = client_ndarray.post("/array_sum", data=test_data)
    assert response.status_code == 200
    assert response.json() == [5, 7, 9]


def test_ndarray_service_array():
    array_sum = ndarray_service.array_sum([1, 2, 3], [4, 5, 6])
    assert isinstance(array_sum, np.ndarray)
    assert all(array_sum == np.array([5, 7, 9]))


def test_row_sum_service_api():
    test_data = json.dumps(
        {"data": {"col1": [1, 2, 3], "col2": [4, 5, 6], "col3": [7, 8, 9]}}
    )
    response = client_row_sum.post("/calculate", data=test_data)
    assert response.status_code == 200
    assert response.json() == [12, 15, 18]


def test_row_sum_service_api_invalid():
    test_data = json.dumps(
        {"data": {"col1": [1, 2, 3], "col2": [4, "I am invalid", 6], "col3": [7, 8, 9]}}
    )
    response = client_row_sum.post("/calculate", data=test_data)
    assert response.status_code == 422
