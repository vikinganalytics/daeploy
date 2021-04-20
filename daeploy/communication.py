import datetime
import logging
from enum import Enum
from typing import List, Callable, Any
import warnings

import requests

from daeploy.utilities import (
    get_daeploy_manager_url,
    get_service_name,
    get_service_version,
    get_headers,
    get_authorized_domains,
    HTTP_METHODS,
)

logger = logging.getLogger(__name__)


requests.packages.urllib3.disable_warnings()  # pylint: disable=no-member
warnings.formatwarning = (
    lambda message, category, filename, lineno, line: f"{message}\n"
)


class DaeploySession(requests.Session):
    def __init__(self, auth_domains: List[str] = None, log_func: Callable = None):
        """A specific requests.Session derivative for daeploy

        Args:
            auth_domains (List[str]): List of domains to which redirection can safely
                be done with kept auth headers. Defaults to None.
            log_func (Callable): Callable that is called with any log messages.
                Defaults to None.

        \f
        # noqa: DAR101,DAR201,DAR401
        """
        super().__init__()
        self._auth_domains = auth_domains or list()
        self._log_func = log_func or logging.getLogger(__name__).warning

    def should_strip_auth(self, old_url: str, new_url: str) -> bool:
        """Overriding `should_strip_auth` of `request.Session` to allow for
        custom logic in terms of when auth header should be removed/kept.

        Args:
            old_url (str): Old url (before redirect)
            new_url (str): New url (suggested redirect)

        Returns:
            bool: True if auth header should be stripped, otherwise False

        \f
        # noqa: DAR101,DAR201,DAR401
        """
        new_host = requests.utils.urlparse(new_url).hostname

        if new_host in self._auth_domains:
            # If we recognize the new host name, keep the Authorization header
            return False

        # Fallback to default behavior
        return super().should_strip_auth(old_url, new_url)

    def request(self, *args, **kwargs):  # pylint: disable=signature-differs
        """Overriding the `request` method on the `Session` object so that
        we can allow retrying if the SSL certificate could not be verified as
        well as raising any errors by default.

        \f
        # noqa: DAR101,DAR201,DAR401
        """
        try:
            # Try with default (verify=True)
            response = super().request(*args, **kwargs)
        except requests.exceptions.SSLError:
            # It failed, log a warning and skip the verification
            self._log_func(
                "WARNING! SSL certificate could not be verified! Daeploy will continue"
                " to work but this potentially makes your solution vulnerable to"
                " Man-in-the-middle attacks! Adding a verifiable certificate is highly"
                " advised!"
            )
            kwargs.update({"verify": False})
            response = super().request(*args, **kwargs)

        response.raise_for_status()
        return response


def request(*args, **kwargs) -> Any:
    """Convenience function for `DaeploySession`

    Returns:
        Any: Whatever `requests.request` returns

    \f
    # noqa: DAR101,DAR201,DAR401
    """

    auth_domains = kwargs.pop("auth_domains", None)
    log_func = kwargs.pop("log_func", None)

    with DaeploySession(auth_domains=auth_domains, log_func=log_func) as session:
        return session.request(*args, **kwargs)


class Severity(Enum):
    """An enumeration of notification severities."""

    INFO = 0
    WARNING = 1
    CRITICAL = 2


def notify(
    msg: str,
    severity: Severity,
    dashboard: bool = True,
    emails: List[str] = None,
    timer: int = 0,
):
    """Generates and sends a notification

    Args:
        msg (str): The message to include for the recipient of the notification.
        severity (Severity): The severity of the notification.
        dashboard (bool): If this is True, the notification will be shown
            on the daeploy dashboard. Defaults to True.
        emails (List[str]): List of emails to send the notifications to.
            Defaults to None, in which case no emails are sent
        timer (int): The amount of time (in seconds) that has to pass
            before the same notification can be send again. Defaults to 0.
    """
    url = f"{get_daeploy_manager_url()}/notifications/"

    timer = 0 if timer < 0 else timer

    payload = {
        "service_name": get_service_name(),
        "service_version": get_service_version(),
        "msg": msg,
        "severity": severity.value,
        "dashboard": dashboard,
        "emails": emails,
        "timer": timer,
        "timestamp": str(datetime.datetime.utcnow()),
    }

    logger.info(f"Notification was posted: {payload} to url: {url}")
    request(
        "POST",
        url,
        auth_domains=get_authorized_domains(),
        headers=get_headers(),
        json=payload,
    )


def call_service(
    service_name: str,
    entrypoint_name: str,
    arguments: dict = None,
    service_version: str = None,
    entrypoint_method: str = "POST",
    **request_kwargs,
) -> Any:
    """Call an entrypoint in a different service.

    Example usage::

        data = call_service(
            service_name="data_connector",
            entrypoint_name="get_data",
            arguments={"variable_name": value}
        )

    Args:
        service_name (str): The service which contains the entrypoint to call.
        entrypoint_name (str): The name of the entrypoint to call.
            The return object(s) of this entrypoint must be jsonable, i.e pass FastAPI's
            jsonable_encoder, otherwise it won't be reachable.
        arguments (dict): Arguments to the entrypoint.
            In the form: {"argument_name": value, ...}. Defaults to None.
        service_version (str): The specific version of the service to call.
            Defaults to None, in which case the main version and the shadows
            versions will be called.
        entrypoint_method (str): HTTP method of the entrypoint to call. You only need
            to change this if you have created an entrypoint with a non-default HTTP
            method. Defaults to "POST".
        **request_kwargs: Keyword arguments to pass on to :func:``requests.post``.

    Raises:
        ValueError: If entrypoint_method is not a valid HTTP method

    Returns:
        Any: The output from the entrypoint in the other service.
    """
    if service_version:
        url = (
            f"{get_daeploy_manager_url()}/services/"
            + f"{service_name}_{service_version}/{entrypoint_name}"
        )
    else:
        url = f"{get_daeploy_manager_url()}/services/{service_name}/{entrypoint_name}"

    entrypoint_method = entrypoint_method.upper()
    if entrypoint_method not in HTTP_METHODS:
        raise ValueError(
            f"Invalid HTTP method: {entrypoint_method}."
            f" Possible options: {HTTP_METHODS}"
        )

    arguments = arguments if arguments else {}

    logger_msg = f"Calling entrypoint: {entrypoint_name} in service: {service_name}"
    if service_version:
        logger_msg += f" ({service_version})"

    logger.info(logger_msg)
    logger.debug(f"Arguments: {arguments}")
    logger.info(f"Sending POST request to: {url}")

    response = request(
        entrypoint_method,
        url=url,
        auth_domains=get_authorized_domains(),
        headers=get_headers(),
        json=arguments,
        **request_kwargs,
    )

    logger.info(
        f"Response from entrypoint: {response.text}, code: {response.status_code}"
    )
    return response.json()
