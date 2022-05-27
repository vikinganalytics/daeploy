"""
Constants and config
"""
import os
from pathlib import Path

# CONSTANTS

DAEPLOY_PREFIX = "daeploy"
DAEPLOY_SERVICE_NAME_KEY = "daeploy.name"
DAEPLOY_SERVICE_VERSION_KEY = "daeploy.version"
DAEPLOY_SERVICE_AUTH_TOKEN_KEY = "daeploy.auth"
DAEPLOY_CONTAINER_TYPE_KEY = "daeploy.type"
DAEPLOY_CONTAINER_TYPE_SERVICE = "service"
DAEPLOY_CONTAINER_TYPE_MANAGER = "manager"
DAEPLOY_CONTAINER_TYPE_PROXY = "proxy"

DAEPLOY_MANAGER_URL_KEY = "DAEPLOY_MANAGER_URL"
DAEPLOY_MANAGER_HOSTNAME_KEY = "DAEPLOY_MANAGER_HOSTNAME"
DAEPLOY_DOCKER_MANAGER_ALIAS = "daeploy-manager"
DAEPLOY_DOCKER_NETWORK = "daeploy-network"

DAEPLOY_DEFAULT_INTERNAL_PORT = 8000
DAEPLOY_FIRST_EXTERNAL_PORT = 8001

DAEPLOY_DEFAULT_S2I_BUILD_IMAGE = "daeploy/s2i-python"
DAEPLOY_ERROR_PORT_ALLOCATED = "port is already allocated"

DAEPLOY_TAR_FILE_NAME = "service.tar.gz"
DAEPLOY_PICKLE_FILE_NAME = "model.pkl"

DAEPLOY_PROXY_DASHBOARD_IDENTIFIER = "proxy_dashboard_configuration"
DAEPLOY_MANAGER_PROXY_CONFIG_FILE = "manager_configuration"
DAEPLOY_AUTH_MIDDLEWARE = "proxy_auth_middleware"
DAEPLOY_AUTH_MIDDLEWARE_IDENTIFIER = f"{DAEPLOY_AUTH_MIDDLEWARE}_configuration"

DAEPLOY_ROOT_DIR = Path(__file__).parent.parent
DAEPLOY_DATA_DIR = DAEPLOY_ROOT_DIR / "data"
DAEPLOY_DATA_DIR.mkdir(exist_ok=True)

DAEPLOY_DEFAULT_VALIDITY = 12  # hours
DAEPLOY_REQUIRED_PASSWORD_LENGTH = 8


# CONFIG


def manager_in_container():
    return bool(
        os.environ.get("DAEPLOY_MANAGER_IN_CONTAINER", "false").lower() == "true"
    )


def get_manager_version():
    return os.environ.get("DAEPLOY_MANAGER_VERSION", "develop")


def get_proxy_domain_name():
    return os.environ.get("DAEPLOY_HOST_NAME", "localhost")


def get_proxy_http_port():
    return os.environ.get("DAEPLOY_PROXY_HTTP_PORT", 5080)


def get_proxy_https_port():
    return os.environ.get("DAEPLOY_PROXY_HTTPS_PORT", 5443)


def get_proxy_config_path():
    return os.environ.get("DAEPLOY_PROXY_CONFIG_PATH", "proxy_config")


def https_proxy():
    return bool(os.environ.get("DAEPLOY_PROXY_HTTPS", "false").lower() == "true")


def letsencrypt_staging_server():
    return bool(
        os.environ.get("DAEPLOY_HTTPS_STAGING_SERVER", "false").lower() == "true"
    )


def get_internal_manager_url():
    return "http://localhost:8000"


def get_external_proxy_url():
    hostname = get_proxy_domain_name()
    port = get_proxy_http_port()
    return f"http://{hostname}:{port}"


def auth_enabled():
    return bool(os.environ.get("DAEPLOY_AUTH_ENABLED", "false").lower() == "true")


def log_level():
    return os.environ.get("DAEPLOY_LOG_LEVEL", "INFO")


def access_logs_enabled():
    return bool(os.environ.get("DAEPLOY_ACCESS_LOGS_ENABLED", "true").lower() == "true")


def configuration_email():
    return os.environ.get("DAEPLOY_CONFIG_EMAIL")


def cors_enabled():
    return os.environ.get("DAEPLOY_ENABLE_CORS")


def cors_allowed_origins():
    """assumes allowed origin are passed as a single string separated by ;
    Example 'https://origin1.com;https://orogin2.com'

    Returns:
        list: url of allowed origins
    """
    return os.environ.get("DAEPLOY_ALLOW_ORIGIN", "").split(";")


def cors_config():
    config = {}
    config["allow_credentials"] = False
    config["allow_origins"] = cors_allowed_origins()
    config["allow_methods"] = ["GET", "POST", "PUT", "DELETE"]
    config["allow_headers"] = ["Authorization"]
    return config


def notification_email_config():
    sender_email = configuration_email()
    sender_pass = os.environ.get("DAEPLOY_CONFIG_EMAIL_PASSWORD")
    smtp_server = os.environ.get("DAEPLOY_NOTIFICATION_SMTP_SERVER")
    smtp_port = os.environ.get("DAEPLOY_NOTIFICATION_SMTP_PORT")
    return sender_email, sender_pass, smtp_server, smtp_port


def get_admin_password():
    return os.environ.get("DAEPLOY_ADMIN_PASSWORD", "admin")
