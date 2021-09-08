import time
import logging
import threading
from typing import List, Dict, Optional, AsyncGenerator
from abc import ABC, abstractmethod
from datetime import datetime

import requests
import docker
import aiodocker

from manager.constants import (
    DAEPLOY_CONTAINER_TYPE_KEY,
    DAEPLOY_CONTAINER_TYPE_SERVICE,
    DAEPLOY_CONTAINER_TYPE_MANAGER,
    DAEPLOY_SERVICE_VERSION_KEY,
    DAEPLOY_SERVICE_NAME_KEY,
    DAEPLOY_MANAGER_URL_KEY,
    DAEPLOY_MANAGER_HOSTNAME_KEY,
    DAEPLOY_DOCKER_MANAGER_ALIAS,
    DAEPLOY_DOCKER_NETWORK,
    DAEPLOY_ERROR_PORT_ALLOCATED,
    DAEPLOY_PREFIX,
    DAEPLOY_FIRST_EXTERNAL_PORT,
    manager_in_container,
    get_proxy_domain_name,
    get_proxy_http_port,
)
from manager.data_models.request_models import BaseService

LOGGER = logging.getLogger(__name__)


def create_container_name(service_name, service_version):
    return f"{DAEPLOY_PREFIX}-{service_name}-{service_version}"


def create_image_name(image_name, image_version):
    return f"{image_name}:{image_version}"


def datetime_to_timestamp(date_time: datetime):
    delta = date_time - datetime.utcfromtimestamp(0)
    return delta.seconds + delta.days * 24 * 3600


class ConnectorBase(ABC):
    @abstractmethod
    def get_services(self):
        pass

    @abstractmethod
    def create_service(
        self,
        image,
        name,
        version,
        internal_port,
        environment_variables=None,
        docker_run_args=None,
    ):
        pass

    @abstractmethod
    def remove_service(self, service):
        pass

    @abstractmethod
    async def service_logs(self, service, tail, follow, since):
        pass


class LocalDockerConnector(ConnectorBase):
    CLIENT = docker.from_env()
    AIO_CLIENT = aiodocker.Docker()

    def __init__(self):
        # Create our own docker network
        try:
            self.CLIENT.networks.create(DAEPLOY_DOCKER_NETWORK, check_duplicate=True)
        except docker.errors.APIError as exc:
            # If the network is already created, just continue.
            # If the errors is something else, raise!
            if (
                f'Conflict ("network with name {DAEPLOY_DOCKER_NETWORK}'
                ' already exists")' not in str(exc)
            ):
                raise

            LOGGER.info(
                f"The docker network {DAEPLOY_DOCKER_NETWORK} already exists, reusing!"
            )

        # Connect the manager container to this network
        # (if the manager is running in a container)
        if manager_in_container():
            manager = self._get_manager_container()
            network = self.CLIENT.networks.get(DAEPLOY_DOCKER_NETWORK)
            if manager not in network.containers:
                network.connect(manager, aliases=[DAEPLOY_DOCKER_MANAGER_ALIAS])
            else:
                LOGGER.info(
                    "Manager already connected to daeploy-network, reusing connection!"
                )

    def _get_manager_container(self) -> docker.models.containers.Container:
        """Returns a reference to the container in which the manager is running

        Raises:
            RuntimeError: If number of manager instances != 1

        Returns:
            Container: Manager container
        """
        matches = self.CLIENT.containers.list(
            filters={
                "label": (
                    f"{DAEPLOY_CONTAINER_TYPE_KEY}={DAEPLOY_CONTAINER_TYPE_MANAGER}"
                )
            },
        )

        if len(matches) > 1:
            raise RuntimeError(
                "Multiple manager instances were found on this docker host! FATAL!"
            )

        if len(matches) < 1:
            raise RuntimeError("Could not find a manager container! FATAL")

        return matches[0]

    def get_service_containers(self) -> List[docker.models.containers.Container]:
        """Returns service containers

        Returns:
            List[Container]: List of service containers
        """
        return self.CLIENT.containers.list(
            all=True,
            filters={
                "label": (
                    f"{DAEPLOY_CONTAINER_TYPE_KEY}={DAEPLOY_CONTAINER_TYPE_SERVICE}"
                )
            },
        )

    def get_services(self) -> List[str]:
        """Returns services

        Returns:
            List[str]: Runtime service names, e.g ["daeploy-myservice-1.0.0"]
        """
        return [c.name for c in self.get_service_containers()]

    def service_version_exists(self, service: BaseService) -> bool:
        """Check if the version of the service already exists!

        Args:
            service (BaseService): The name and version of the service.

        Returns:
            bool: Returns True if version of the service exists, else False
        """
        try:
            self.CLIENT.containers.get(
                create_container_name(service.name, service.version)
            )
            return True
        except (docker.errors.NotFound, requests.exceptions.ChunkedEncodingError):
            return False

    def image_exists_in_running_service(self, name, version):
        """Checks if an image exists in a running service.

        Args:
            name (str): The name of the image
            version (str): The version of the image

        Returns:
            bool: True if the image exists in a running service, else False
        """
        image = create_image_name(name, version)
        images = [(c.image.tags or [""])[0] for c in self.get_service_containers()]
        return image in images

    def remove_image_if_exists(self, name, version):
        """Removes image if it exists

        Args:
            name (str): The name of the image to remove
            version (str): The version of the image to remove
        """
        image_name = create_image_name(name, version)
        try:
            image = self.CLIENT.images.get(image_name)
            self.CLIENT.images.remove(image.id, force=True)
            LOGGER.info(f"Deleted image: {image_name}")
        except docker.errors.ImageNotFound:
            LOGGER.info(f"Image: {image_name} did not already exist.")
        except docker.errors.APIError:
            LOGGER.exception(f"Failed to delete image {image_name}")

    def create_service(
        self,
        image: str,
        name: str,
        version: str,
        internal_port: int,
        environment_variables: Dict[str, str] = None,
        docker_run_args: Dict = None,
    ) -> str:
        """Starts a container using the provided image in detached mode

        Args:
            image (str): Image to use
            name (str): Service name
            version (str): Service version
            internal_port (int): Internal port in container that should
                be exposed to external access
            environment_variables (dict): Extra needed environment variables.
            docker_run_args (Dict): Extra key-value arguments for docker run command.

        Returns:
            str: URL to the service.

        Raises:
            docker.errors.APIError: If the shit hits the fan when trying to use docker
        """
        environment_variables = environment_variables or {}
        container_name = create_container_name(name, version)

        # The external port, and hence the while-loop, is only here for
        # compatibility with our dev environment (WSL2 + docker) which does
        # not allow to access docker container through their private ips
        external_port = DAEPLOY_FIRST_EXTERNAL_PORT

        # Find an identifier (hostname or ip ) to the manager
        manager_identifier = (
            DAEPLOY_DOCKER_MANAGER_ALIAS if manager_in_container() else "172.17.0.1"
        )

        # Standard environment variables
        standard_environment_variables = {
            DAEPLOY_MANAGER_URL_KEY: (
                f"http://{manager_identifier}:{get_proxy_http_port()}"
            ),
            DAEPLOY_MANAGER_HOSTNAME_KEY: get_proxy_domain_name(),
            DAEPLOY_SERVICE_NAME_KEY: name,
            DAEPLOY_SERVICE_VERSION_KEY: version,
        }

        # Assemble inputs
        run_kwargs = docker_run_args or {}

        # Basics
        run_kwargs.update(
            {
                "image": image,
                "name": container_name,
                "network": DAEPLOY_DOCKER_NETWORK,
                "detach": True,
                "log_config": docker.types.LogConfig(
                    type=docker.types.LogConfig.types.JSON,
                    config={"max-size": "100m", "max-file": "3"},
                ),
            }
        )

        # Labels
        run_kwargs["labels"] = {
            **run_kwargs.get("labels", dict()),
            **{DAEPLOY_CONTAINER_TYPE_KEY: DAEPLOY_CONTAINER_TYPE_SERVICE},
        }

        # Env variables
        run_kwargs["environment"] = {
            **run_kwargs.get("environment", dict()),
            **{
                **environment_variables,
                **standard_environment_variables,
            },
        }

        # Ports
        run_kwargs["ports"] = run_kwargs.get("ports", dict())

        while True:
            try:
                # Set port!
                run_kwargs["ports"][internal_port] = external_port

                # We dont need the external ports when the manage runs in a container
                if manager_in_container():
                    del run_kwargs["ports"][internal_port]

                # Start container
                container = self.CLIENT.containers.run(**run_kwargs)

                # If we get to here, container is running!
                # Let it run for 5 seconds an then update restart policy to "always"
                # This "should" be working out of the box according to the docs for
                # `docker run`, but doesnt... So reimplementing here but with 5 seconds.
                # https://docs.docker.com/config/containers/start-containers-automatically/#use-a-restart-policy
                # https://github.com/docker/compose/issues/7619
                # https://github.com/docker/compose/issues/8010
                def _update_restart_policy():
                    time.sleep(5)
                    try:
                        LOGGER.info(f"Updating restart policy on {container}")
                        container.update(
                            restart_policy={"Name": "always"},
                        )
                    except docker.errors.APIError:
                        # Not much we can do if it fails
                        # Most probably, the container no longer exists
                        LOGGER.info(f"Failed to update restart policy on {container}")

                # Using a separate thread for this, since we dont want to wait
                threading.Thread(target=_update_restart_policy, daemon=True).start()

                break  # break out of while loop after successful startup
            except docker.errors.APIError as exc:
                if DAEPLOY_ERROR_PORT_ALLOCATED in str(exc):
                    LOGGER.info(
                        f"Port {external_port} already in use, trying next one!"
                    )
                    # Port already taken, try next one and remove created container
                    self.CLIENT.containers.get(container_name).remove(force=True)
                    external_port += 1
                else:
                    raise

        if manager_in_container():
            # As in a production setup! Manager container is part of the same
            # docker network as the service, lets use container names for communication
            # NOTE: Internal port can be used here (docker black magic!)
            return f"http://{container_name}:{internal_port}"

        # Running as part of dev/debug setup
        return f"http://localhost:{external_port}"

    def remove_service(self, service: BaseService):
        """Kill specific version of the service

        Args:
            service (BaseService): The name and version of the service to remove
        """

        container = self.CLIENT.containers.get(
            create_container_name(service.name, service.version)
        )
        LOGGER.debug(f"Removing container with container_id: {container.id}")

        container.remove(force=True)  # Remove the container

    def inspect_service(self, service: BaseService) -> dict:
        """Inspect the container of the service

        Args:
            service (BaseService): The name and version of the service to inspect.

        Returns:
            dict: Inspected container state
        """
        container = self.CLIENT.containers.get(
            create_container_name(service.name, service.version)
        )
        return container.client.api.inspect_container(container.id)

    async def service_logs(
        self,
        service: BaseService,
        tail: Optional[int] = None,
        follow: Optional[bool] = False,
        since: Optional[datetime] = None,
    ) -> AsyncGenerator[str, None]:
        """Returns logs from the service

        Args:
            service (BaseService): The service to get the logs from.
            tail (Optional[int]): The number of lines to output from the end of the
                logs. Default to None, meaning that all logs will be shown.
            follow (Optional[bool]): If the logs should be followed.
                Default to False.
            since (Optional[datetime]): Get logs since given datetime. Default to None.

        Yields:
            AsyncGenerator[str, None]: Async infinite generator if following,
            else async finite generator.
        """
        container = await self.AIO_CLIENT.containers.get(
            create_container_name(service.name, service.version)
        )

        kwargs = {
            "tail": tail if tail else "all",
            "stdout": True,
            "stderr": True,
            "follow": follow,
        }

        if since:
            kwargs["since"] = datetime_to_timestamp(since)
        logs = container.log(**kwargs)

        if follow:
            async for log in logs:
                yield log
        else:
            for log in await logs:
                yield log

    def manager_logs(self, since: datetime) -> str:
        """Get the manager logs from a certain time

        Args:
            since (datetime): Get logs from this time to now (UTC).

        Returns:
            str: Manager logs
        """
        manager_container = self._get_manager_container()
        return manager_container.logs(since=since)


RTE_CONN = LocalDockerConnector()
