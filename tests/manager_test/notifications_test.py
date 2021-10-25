import pytest
from unittest.mock import patch
import datetime
import time

from manager.routers import notification_api
from manager.data_models.request_models import NotificationRequest

TEST_EMAIL_ADDRESS = "notify@multiviz.se"

notification_api.EMAIL_CONFIG = (
    TEST_EMAIL_ADDRESS,
    "#Yh13G!SBM%KBN",
    "mail.multiviz.se",
    465,
)
(
    notification_api.SENDER_EMAIL,
    notification_api.SENDER_PASS,
    notification_api.SMTP_SERVER,
    notification_api.SMTP_PORT,
) = notification_api.EMAIL_CONFIG


# Notification without any timer.
notification_1 = NotificationRequest(
    service_name="service1",
    service_version="0.0.1",
    msg="Oh no!",
    severity=3,
    dashboard=True,
    emails=None,
    timer=0,
    timestamp=str(datetime.datetime.utcnow()),
)

# Notificaiton with 5s timer.
notification_2 = NotificationRequest(
    service_name="service2",
    service_version="0.0.1",
    msg="Oh yes!",
    severity=0,
    dashboard=True,
    emails=None,
    timer=5,
    timestamp=str(datetime.datetime.utcnow()),
)

# Notificaiton with 5s timer and active email.
notification_3 = NotificationRequest(
    service_name="service3",
    service_version="0.0.1",
    msg="Oh email!",
    severity=0,
    dashboard=True,
    emails=[TEST_EMAIL_ADDRESS],
    timer=5,
    timestamp=str(datetime.datetime.utcnow()),
)


@pytest.fixture
def notifications_dict():
    try:
        # Reset notifications between tests
        notification_api.NOTIFICATIONS = {}
    finally:
        # Clean up after test
        notification_api.NOTIFICATIONS = {}


def test_register_two_different_notifications_different_key(notifications_dict):
    notification_api.register_notification(notification_1)
    notification_api.register_notification(notification_2)
    assert len(notification_api.NOTIFICATIONS.keys()) == 2


def test_register_two_of_the_same_notification_same_key(notifications_dict):
    notification_api.register_notification(notification_1)
    notification_api.register_notification(notification_1)

    notification_hash = notification_1.__hash__()

    assert len(notification_api.NOTIFICATIONS.keys()) == 1
    assert notification_api.NOTIFICATIONS[notification_hash]["counter"] == 2


def test_new_notification_frozen(notifications_dict):
    notification_api.new_notification(notification_2)
    notification_api.NOTIFICATIONS[notification_2.__hash__()][
        "frozen_until"
    ] > datetime.datetime.utcnow()


@patch("manager.notification_api._send_notification_as_email")
def test_email_notification_not_send_when_frozen(email_func, notifications_dict):
    notification_api.new_notification(notification_3)
    notification_api.new_notification(notification_3)
    # The email func is only called once!
    email_func.called_once()


@patch("manager.notification_api._send_notification_as_email")
def test_email_notification_send_when_not_frozen(email_func, notifications_dict):
    # This first notification should be send
    notification_api.new_notification(notification_3)
    # This 2nd notification should be blocked since frozen
    notification_api.new_notification(notification_3)
    # Wait out the freeze time
    time.sleep(5)
    # This third notification should be send
    notification_api.new_notification(notification_3)
    # Grace period for joining threads etc
    time.sleep(1)
    assert email_func.call_count == 2


def test_email_sent():
    notification_api._send_notification_as_email(notification_3)
