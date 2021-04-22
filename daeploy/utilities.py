import logging
import os
import re

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


def get_db_table_limit() -> int:
    """Limit of rows or duration to keep records in service database.
    Reads from the environment variable DAEPLOY_SERVICE_DB_TABLE_LIMIT.

    Returns:
        tuple:

            - int: Maximum rows/days etc. of database. Defaults to 365
            - str: One of rows, days, hours, minutes, seconds. Defaults to "days"
    """
    number_pattern = r"\d+"
    setting_pattern = r"[A-Za-z]+"
    table_limit = os.environ.get("DAEPLOY_SERVICE_DB_TABLE_LIMIT", "365days")
    if re.fullmatch(number_pattern + setting_pattern, table_limit):
        number = int(re.search(number_pattern, table_limit).group(0))
        setting = re.search(setting_pattern, table_limit).group(0).lower()

        if setting in ["rows", "days", "hours", "minutes", "seconds"]:
            return number, setting

    LOGGER.error(
        "Wrong format of environment variable DAEPLOY_SERVICE_DB_TABLE_LIMIT."
        " It should be a number followed by rows, days, hours, minutes or"
        " seconds. Using standard value 365days."
    )
    return 365, "days"
