"""
File used as a service in e2e tests.
"""

import logging

from daeploy import service
from daeploy.communication import call_service

logger = logging.getLogger(__name__)
logging.getLogger("daeploy").setLevel(logging.DEBUG)


@service.entrypoint
def call_downstream_method(service_name, entrypoint_name, arguments):
    greeting = call_service(
        service_name=service_name, entrypoint_name=entrypoint_name, arguments=arguments
    )
    logger.debug(greeting)
    return greeting


@service.entrypoint
def call_downstream_get_method(service_name):
    response = call_service(
        service_name=service_name, entrypoint_name="get_method", entrypoint_method="GET"
    )
    return response


if __name__ == "__main__":
    service.run()
