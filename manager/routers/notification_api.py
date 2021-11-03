import logging
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Sequence
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from manager.data_models.request_models import NotificationRequest
from manager.constants import notification_email_config, get_proxy_domain_name

LOGGER = logging.getLogger(__name__)
ROUTER = APIRouter()
HOST = get_proxy_domain_name()

THREAD_POOL = ThreadPoolExecutor(max_workers=8)

NOTIFICATIONS = {}

EMAIL_CONFIG = notification_email_config()
SENDER_EMAIL, SENDER_PASS, SMTP_SERVER, SMTP_PORT = EMAIL_CONFIG


@ROUTER.get("/")
def get_notifications():
    return NOTIFICATIONS


@ROUTER.delete("/")
def delete_notifications():
    """Deletes all notifications"""
    NOTIFICATIONS.clear()


@ROUTER.post("/")
def new_notification(notification: NotificationRequest):
    """Handles the incoming notification.
    Registers the notification and sends the notification
    if it is not frozen.

    \f
    Args:
        notification (NotificationRequest): The notification.

    Returns:
        str: Response message.
    """
    LOGGER.info("Register new notification")
    register_notification(notification)

    if not notification_is_frozen(notification):
        if notification.emails and all(EMAIL_CONFIG):
            LOGGER.warning("Sending email notification")
            THREAD_POOL.submit(_send_notification_as_email, notification)
        update_freeze_time(notification)
    else:
        LOGGER.warning("Notification is frozen")

    return "Notification added"


def register_notification(notification: NotificationRequest):
    """Registers the notification in the local variable 'notifications'.
    The hash of the notification is computed and used as the key.

    If the hash of the notification already exists,
    the counter and timestamp field for the notification is updated.

    Args:
        notification (NotificationRequest): The notification.
    """
    notification_hash = hash(notification)

    if notification_hash in NOTIFICATIONS:
        NOTIFICATIONS[notification_hash]["counter"] += 1
        NOTIFICATIONS[notification_hash]["timestamp"] = notification.timestamp
    else:
        NOTIFICATIONS[notification_hash] = notification.dict()
        NOTIFICATIONS[notification_hash]["counter"] = 1
        # If the notification uses the timer, inititate the frozen_until field.
        # We set the frozen_until time to current time since we do not want the
        # freeze the first occurance of this notification.
        if notification.timer != 0:
            NOTIFICATIONS[notification_hash][
                "frozen_until"
            ] = datetime.datetime.utcnow()


def notification_is_frozen(notification: NotificationRequest):
    """Checks if the 'notification' is frozen or not.

    Args:
        notification (NotificationRequest): The notification

    Returns:
        bool: True if the notification is frozen, else False.
    """
    notification_hash = hash(notification)
    if NOTIFICATIONS[notification_hash]["timer"] == 0:
        return False
    return (
        NOTIFICATIONS[notification_hash]["frozen_until"] >= datetime.datetime.utcnow()
    )


def update_freeze_time(notification: NotificationRequest):
    """Updates the freeze time for the notification with hash 'notification_hash'

    Args:
        notification (NotificationRequest): The notification.
    """
    notification_hash = hash(notification)
    # A notification with timer == 0 can never be frozen.
    if not NOTIFICATIONS[notification_hash]["timer"] == 0:
        NOTIFICATIONS[notification_hash][
            "frozen_until"
        ] = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=NOTIFICATIONS[notification_hash]["timer"]
        )


def _send_email(recipient_emails: Sequence[str], subject: str, email_content: str):
    """Sends an email to each recipient email address.

    Args:
        recipient_emails (Sequence[str]): Sequence with recipient emails
            addresses as strings
        subject (str): Subject of the email
        email_content (str): Content of the email
    """
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL
    message["To"] = ", ".join(recipient_emails)

    mime_text = MIMEText(email_content, "html")
    message.attach(mime_text)
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, recipient_emails, message.as_string())


def _send_notification_as_email(notification: NotificationRequest):
    """Sends a notification email.

    Args:
        notification (NotificationRequest): The API notification requests.
    """

    service = f"{notification.service_name} {notification.service_version}"
    severities = {0: "Info", 1: "Warning", 2: "Critical"}
    severity = severities.get(notification.severity, notification.severity)

    subject = f"DAEPLOY-ALARM: {severity} - {service}"
    content = f"""\
        <h1>An alarm has been triggered in \
        <span style="color: #eb3a2a;">{service}</span></h1>
        <p><strong>Message:</strong> {notification.msg}</p>
        <p><strong>Severity:</strong> {severity}</p>
        <p><strong>Host:</strong> {HOST}</p>
    """
    _send_email(notification.emails, subject, content)


def _manager_notification(msg):
    return NotificationRequest(
        service_name="Manager",
        service_version="",
        msg=msg,
        severity=1,
        dashboard=True,
        emails=None,
        timer=0,
        timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    )


def check_email_config():
    if not SENDER_EMAIL:
        msg = (
            "No sender email configured. Should be set as environment variable"
            '"DAEPLOY_CONFIG_EMAIL" when starting manager.'
        )
        register_notification(_manager_notification(msg))

    if not SENDER_PASS:
        msg = (
            "No sender email password configured. Should be set as environment"
            'variable "DAEPLOY_CONFIG_EMAIL_PASSWORD" when starting'
            "manager."
        )
        register_notification(_manager_notification(msg))

    if not SMTP_SERVER:
        msg = (
            "No smtp server configured. Should be set as environment"
            'variable "DAEPLOY_NOTIFICATION_SMTP_SERVER" when starting'
            "manager."
        )
        register_notification(_manager_notification(msg))

    if not SMTP_PORT:
        msg = (
            "No smtp server port configured. Should be set as environment"
            'variable "DAEPLOY_NOTIFICATION_SMTP_PORT" when starting'
            "manager."
        )
        register_notification(_manager_notification(msg))

    subject = "DAEPLOY-EMAIL CONNECTION"
    content = f"""\
        <h1>An email connection has been established with the daeploy manager</h1>
        <p>Email notifications from services running on host <strong>{HOST}</strong>\
        can now be sent using this email address.</p>
    """

    try:
        _send_email([SENDER_EMAIL], subject, content)
    except (smtplib.SMTPException, OSError) as exc:
        msg = (
            "Could not connect to the SMTP server. "
            "Cannot guarantee that email notifications get sent. "
            f"Error Message: {str(exc)}"
        )
        register_notification(_manager_notification(msg))
        LOGGER.exception(msg)


if any(EMAIL_CONFIG):
    check_email_config()
