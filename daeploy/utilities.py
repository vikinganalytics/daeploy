import logging
import os
import re
from typing import List, Tuple
from datetime import timedelta

LOGGER = logging.getLogger(__name__)

UNKNOWN_NAME = "unknown"
UNKNOWN_VERSION = "0.0.0"
HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "TRACE", "PATCH"]


def get_daeploy_manager_url() -> str:
    """Returns a URL where the manager currently running
    this service can be reached.

    Returns:
        str: URL to manager
    """
    return os.environ.get("DAEPLOY_MANAGER_URL", "http://host.docker.internal")


def get_daeploy_manager_hostname() -> str:
    """Returns the hostname of the manager currently running
    this service.

    Returns:
        str: Hostname of manager
    """
    return os.environ.get("DAEPLOY_MANAGER_HOSTNAME", "localhost")


def get_service_name() -> str:
    """Name of this service

    Returns:
        str: Name
    """
    return os.environ.get("daeploy.name", UNKNOWN_NAME)


def get_service_version() -> str:
    """Versio of this service

    Returns:
        str: Version string (ex. 1.2.3)
    """
    return os.environ.get("daeploy.version", UNKNOWN_VERSION)


def get_service_access_token() -> str:
    """Returns a valid access token for communicating with
    the manager currently running this service and other services
    running on that manager.

    Returns:
        str: JWT token
    """
    return os.environ.get("daeploy.auth", "unknown")


def get_service_root_path() -> str:
    """Returns the root path at which this service is running.
    Can be for example `/services/<service_name>_<service_version>`

    Returns:
        str: Root path
    """
    name = get_service_name()
    version = get_service_version()

    if name == UNKNOWN_NAME and version == UNKNOWN_VERSION:
        return ""

    return f"/services/{name}_{version}"


def get_headers() -> dict:
    """Generating headers for API calls

    Returns:
        dict: Assembled header
    """
    return {
        "Authorization": f"Bearer {get_service_access_token()}",
        "Content-Type": "application/json",
        "Host": get_daeploy_manager_hostname(),
    }


def get_authorized_domains() -> list:
    """Returns list of autorized domains for auth header

    Returns:
        list: List of authorized domains
    """
    return [get_daeploy_manager_hostname()]


def match_limit_and_unit(string: str, accepted_units: List[str]) -> Tuple[str]:
    limit_pattern = r"\d+"
    unit_pattern = r"[A-Za-z]+"
    if re.fullmatch(limit_pattern + unit_pattern, string):
        number = int(re.search(limit_pattern, string).group(0))
        setting = re.search(unit_pattern, string).group(0).lower()

        if setting in accepted_units:
            return number, setting

    raise ValueError(
        "Invalid format of environment variable {env_var}."
        " It should be a number followed by 'rows', 'days', 'hours', 'minutes' or"
        " 'seconds'. Using standard value {default_limit}{default_unit}."
    )


def get_db_table_limit() -> Tuple[int]:
    """Limit of rows or duration to keep records in service database.
    Reads from the environment variable DAEPLOY_SERVICE_DB_TABLE_LIMIT.
    Data will be cleaned in intervals, defined by the environment variable
    DAEPLOY_SERVICE_DB_CLEAN_INTERVAL.

    Returns:
        tuple:

            - int: Maximum rows/days etc. of database. Defaults to 90
            - str: One of rows, days, hours, minutes, seconds. Defaults to "days"
    """
    default_limit = 90
    default_unit = "days"
    env_var = "DAEPLOY_SERVICE_DB_TABLE_LIMIT"

    table_limit = os.environ.get(env_var, f"{default_limit}{default_unit}")
    try:
        return match_limit_and_unit(
            table_limit, ["rows", "days", "hours", "minutes", "seconds"]
        )
    except ValueError as exc:
        msg = str(exc).format(
            env_var=env_var, default_limit=default_limit, default_unit=default_unit
        )
        LOGGER.error(msg)
    return default_limit, default_unit


def get_db_clean_interval_seconds() -> float:
    """Converts the environment variable DAEPLOY_SERVICE_DB_CLEAN_INTERVAL,
    that defines how often to clean the database from old records, into seconds
    and returns that.

    Returns:
        float: Seconds between cleans. Defaults to 7 days
    """

    default_interval = 7
    default_unit = "days"
    env_var = "DAEPLOY_SERVICE_DB_CLEAN_INTERVAL"

    table_limit = os.environ.get(env_var, f"{default_interval}{default_unit}")
    try:
        interval, unit = match_limit_and_unit(
            table_limit, ["days", "hours", "minutes", "seconds"]
        )
    except ValueError as exc:
        msg = str(exc).format(
            env_var=env_var, default_limit=default_interval, default_unit=default_unit
        )
        LOGGER.error(msg)
        interval, unit = default_interval, default_unit

    return timedelta(**{unit: interval}).total_seconds()
