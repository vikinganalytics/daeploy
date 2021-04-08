import time
import logging
import shutil
import subprocess
from typing import List, Union
from pathlib import Path

import toml

from manager.notification_api import _manager_notification, register_notification
from manager.constants import (
    DAEPLOY_PROXY_DASHBOARD_IDENTIFIER,
    DAEPLOY_MANAGER_IDENTIFIER,
    DAEPLOY_AUTH_MIDDLEWARE,
    DAEPLOY_AUTH_MIDDLEWARE_IDENTIFIER,
    DAEPLOY_DATA_DIR,
    get_proxy_config_path,
    get_proxy_domain_name,
    get_proxy_http_port,
    get_proxy_https_port,
    get_internal_manager_url,
    auth_enabled,
    https_proxy,
    configuration_email,
    letsencrypt_staging_server,
)
from manager.exceptions import TraefikError

LOGGER = logging.getLogger(__name__)


def get_static_config_path():
    return Path(get_proxy_config_path())


def get_dynamic_config_path():
    return get_static_config_path() / Path("dynamic")


def run_proxy():
    """Starts a traefik instance and register an atexit handler for shutdown

    Returns:
        object: Function handle for stopping proxy

    Raises:
        TraefikError: If Traefik could not start up properly.

    """

    LOGGER.info("Starting traefik proxy!")
    config_file_path = (get_static_config_path() / Path("traefik.toml")).resolve()
    process = subprocess.Popen(
        ["traefik", "--configfile", str(config_file_path), "--accesslog=true"],
        stdout=None,
        stderr=None,
    )

    # Grace period
    time.sleep(1)

    # Check that traefik started without any trouble
    if process.poll():
        _, stderr = process.communicate()
        LOGGER.error("Traefik could not start!")
        LOGGER.error(f"Traefik return code: {process.returncode}")
        LOGGER.error(stderr)
        raise TraefikError("Traefik could not start! Check the logs!")

    def cleanup():
        process.kill()
        shutil.rmtree(get_static_config_path())

    return cleanup


def write_toml_file(file_path: Path, content: dict):
    """Writes a configuration file with 'content' to
    'file_path'

    Args:
        file_path (Path): Path to file that will be written
        content (dict): Content to write
    """
    LOGGER.info(f"Writing configuration file: {file_path}")
    LOGGER.debug(f"with content: {content}")
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open(mode="w") as file_handle:
        toml.dump(
            content,
            file_handle,
        )


def delete_toml_file(file_path: Path):
    """Remove a configuration file at 'file_path'

    Args:
        file_path (Path): Path to file that will be removed
    """
    LOGGER.info(f"Deleting configuration file: {file_path}")
    try:
        file_path.unlink()
    except FileNotFoundError:
        # Path.unlink(missing_ok=True) gives same behavior but was
        # not introduced until python 3.8
        pass


def write_static_configuration():
    """Writes a predefined static configuration file for the proxy"""
    static_config = {
        "entryPoints": {
            "web": {
                "address": f":{get_proxy_http_port()}",
            },
            "websecure": {
                "address": f":{get_proxy_https_port()}",
            },
        },
        "providers": {
            "providersThrottleDuration": "0.5s",
            "file": {
                "directory": str(get_dynamic_config_path().resolve()),
                "watch": True,
            },
        },
        "api": {
            "dashboard": True,
        },
    }

    email = configuration_email()
    if https_proxy():
        acme_path = DAEPLOY_DATA_DIR / "acme.json"

        if not email:
            msg = (
                "For HTTPS we recommend you set an email address with"
                " the DAEPLOY_CONFIG_EMAIL environment variable, to get notified about"
                " your certificates."
            )
            LOGGER.warning(msg)
            register_notification(_manager_notification(msg))

        static_config["entryPoints"]["web"]["http"] = {
            "redirections": {
                "entryPoint": {
                    "to": "websecure",
                    "scheme": "https",
                }
            }
        }

        static_config["certificatesResolvers"] = {
            "cert-resolver": {
                "acme": {
                    "email": email or "dummy@email.com",
                    "storage": str(acme_path),
                    "httpChallenge": {"entryPoint": "web"},
                }
            }
        }

        if letsencrypt_staging_server():
            static_config["certificatesResolvers"]["cert-resolver"]["acme"][
                "caServer"
            ] = "https://acme-staging-v02.api.letsencrypt.org/directory"

    # Make sure the dynamic path exists
    get_dynamic_config_path().mkdir(parents=True, exist_ok=True)

    # Write static configuration
    LOGGER.info("Writing static configuration file")
    write_toml_file(get_static_config_path() / Path("traefik.toml"), static_config)


def add_dynamic_configuration(file_name: str, content: dict):
    """Add a single file dynamic configuration

    Args:
        file_name (str): Name of file to be added
        content (dict): Content of file
    """
    file_path = get_dynamic_config_path() / Path(file_name).with_suffix(".toml")

    write_toml_file(file_path, content)


def remove_dynamic_configuration(file_name: str):
    """Remove a single file dynamic configuration

    Args:
        file_name (str): Name of file to be removed
    """

    file_path = get_dynamic_config_path() / Path(file_name).with_suffix(".toml")
    delete_toml_file(file_path)


def get_router_configuration(
    rule: str,
    service: str,
    middlewares: Union[List[str], None],
    tls: bool,
) -> dict:
    """Get the router configuration for one rule.

    Args:
        rule (str): Router rule
        service (str): Service name to run on the router
        middlewares (Union[List[str], None]): Any middlewared associated with the router
        tls (bool): Should the router have TLS

    Returns:
        dict: Router configuration
    """
    config = {
        "rule": rule,
        "service": service,
    }
    if tls:
        config["tls"] = {"certresolver": "cert-resolver"}
    if middlewares:
        config["middlewares"] = middlewares

    return config


def get_proxy_dashboard_configuration() -> dict:
    """Returns configuration for the traefik internal dashboard

    Returns:
        dict: configuration
    """
    rule = f"""Host(`{get_proxy_domain_name()}`) && \
        (PathPrefix(`/proxy/dashboard`) || PathPrefix(`/api`))"""

    config = {
        "http": {
            "routers": {
                "traefik_dashboard": get_router_configuration(
                    rule=rule,
                    service="api@internal",
                    middlewares=["traefik-dashboard-prefix-stripper"],
                    tls=https_proxy(),
                )
            },
            "middlewares": {
                "traefik-dashboard-prefix-stripper": {
                    "stripPrefix": {"prefixes": ["/proxy"], "forceSlash": False}
                }
            },
        }
    }

    if auth_enabled():
        config["http"]["routers"]["traefik_dashboard"]["middlewares"].append(
            DAEPLOY_AUTH_MIDDLEWARE
        )

    return config


def get_manager_configuration() -> dict:
    """Returns configuration for the manager dashboard

    Returns:
        dict: configuration
    """
    rule = f"""Host(`{get_proxy_domain_name()}`)"""
    rule_login = f"""Host(`{get_proxy_domain_name()}`) && PathPrefix(`/auth/login`)"""

    config = {
        "http": {
            "routers": {
                "manager": get_router_configuration(
                    rule=rule,
                    service="manager_service",
                    middlewares=None,
                    tls=https_proxy(),
                ),
                "login_page": get_router_configuration(
                    rule=rule_login,
                    service="manager_service",
                    middlewares=None,
                    tls=https_proxy(),
                ),
            },
            "services": {
                "manager_service": {
                    "loadBalancer": {
                        "servers": [
                            {
                                "url": get_internal_manager_url(),
                            }
                        ]
                    }
                }
            },
        }
    }

    if auth_enabled():
        config["http"]["routers"]["manager"]["middlewares"] = [DAEPLOY_AUTH_MIDDLEWARE]

    return config


def get_auth_middleware_configuration() -> dict:
    """Returns configuration for the auth middleware

    Returns:
        dict: configuration
    """
    return {
        "http": {
            "middlewares": {
                DAEPLOY_AUTH_MIDDLEWARE: {
                    "forwardAuth": {
                        "address": f"{get_internal_manager_url()}/auth/verify",
                    }
                }
            }
        }
    }


def initial_setup():
    """Perform initial setup of proxy

    Returns:
        object: Function handle to kill proxy and clean up configuration files
    """

    # Create and write static configuration
    write_static_configuration()

    # Add core dynamic configurations
    add_dynamic_configuration(
        DAEPLOY_PROXY_DASHBOARD_IDENTIFIER, get_proxy_dashboard_configuration()
    )

    # Add manager to root
    add_dynamic_configuration(DAEPLOY_MANAGER_IDENTIFIER, get_manager_configuration())

    # Add auth middleware
    add_dynamic_configuration(
        DAEPLOY_AUTH_MIDDLEWARE_IDENTIFIER, get_auth_middleware_configuration()
    )

    # Start traefik and return function handle for cleaning up
    return run_proxy()


def get_base_service_config(service_name: str) -> dict:
    """Returns a standard service configuration with routing and prefix stripper.
    Only the actual service is missing.

    Args:
        service_name (str): Name of the service to create the base config for

    Returns:
        dict: Routing and prefix configuration
    """
    path_prefix = f"/services/{service_name}"
    prefix_strip_middleware = f"{service_name}_prefix_stripper"
    rule = f"Host(`{get_proxy_domain_name()}`) && PathPrefix(`{path_prefix}`)"

    config = {
        "http": {
            "routers": {
                service_name: get_router_configuration(
                    rule=rule,
                    service=service_name,
                    middlewares=[prefix_strip_middleware],
                    tls=https_proxy(),
                ),
            },
            "middlewares": {
                prefix_strip_middleware: {
                    "stripPrefix": {"prefixes": [path_prefix], "forceSlash": False}
                }
            },
            "services": {},
        }
    }

    if auth_enabled():
        config["http"]["routers"][service_name]["middlewares"].append(
            DAEPLOY_AUTH_MIDDLEWARE
        )

    return config


def create_new_service_configuration(name: str, version: str, address: str):
    """Creates a dymanic configuration file for a new service.

    Args:
        name (str): Name of the service
        version (str): version of the service
        address (str): URL to the service
    """
    LOGGER.info(f"Creating configuration for service: {name}")
    service_name = f"{name}_{version}"
    file_name = f"{service_name}_configuration.toml"
    config = get_base_service_config(service_name)

    # Create service configurations
    services = {}
    services[service_name] = {
        "loadBalancer": {
            "servers": [
                {
                    "url": address,
                }
            ]
        }
    }

    config["http"]["services"] = services

    add_dynamic_configuration(file_name, config)


def create_mirror_configuration(
    name: str, main_version: str, shadow_versions: List[str] = None
):
    """Sets up a configuration file for shadow deployment. Where any calls sent
    to /services/service_version is mirrored to all services with that name.

    Args:
        name (str): Name of the service
        main_version (str): Version of the main service
        shadow_versions (List[str], optional): List of versions of the shadow
            services. Defaults to None.
    """
    file_name = f"{name}_configuration.toml"
    config = get_base_service_config(name)

    shadow_versions = shadow_versions or []
    mirrors = [{"name": f"{name}_{ver}", "percent": 100} for ver in shadow_versions]

    main_service_name = f"{name}_{main_version}"
    services = {}
    services[name] = {
        "mirroring": {
            "service": main_service_name,
            "mirrors": mirrors,
        }
    }

    config["http"]["services"] = services

    add_dynamic_configuration(file_name, config)


def remove_service_configuration(name: str, version: str):
    """Remove a service configuration.

    Args:
        name (str): Service name
        version (str): Service version
    """
    service_name = f"{name}_{version}"
    file_name = f"{service_name}_configuration.toml"
    mirror_file_name = f"{name}_configuration.toml"
    remove_dynamic_configuration(file_name)
    remove_dynamic_configuration(mirror_file_name)
