from fastapi.testclient import TestClient

import examples.notifications_example.service as service
from daeploy.testing import patch

app = service.service.app
test_client = TestClient(app)


def test_notification_called():
    with patch("examples.notifications_example.service.notify") as notify:
        response = test_client.post("/hello", json={"name": "World"})
        notify.assert_called_once()
        assert response.status_code == 403


def test_accepted_call():
    with patch("examples.notifications_example.service.notify") as notify:
        response = test_client.post("/hello", json={"name": "Bengt"})
        assert not notify.called
        assert response.status_code == 200
