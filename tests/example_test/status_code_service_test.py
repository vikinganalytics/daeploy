import json

from fastapi.testclient import TestClient
import examples.status_code_example.service as status_service

app = status_service.service.app
client = TestClient(app)


def test_status_codes():
    test_data = json.dumps({"dict_name": "test", "content": {"content": "dict"}})

    # Valid request
    response = client.post("/create_new_dict", data=test_data)
    assert response.status_code == 201

    # Invalid request
    response = client.post("/create_new_dict", data=test_data)
    assert response.status_code == 409


def test_get_dict():
    test_data = json.dumps({"dict_name": "test"})

    response = client.post("/get_dict", data=test_data)
    assert response.status_code == 200
    assert response.json() == {"content": "dict"}
