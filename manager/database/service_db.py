import logging
from typing import List, Tuple
from uuid import UUID

from sqlalchemy import and_, not_
from sqlalchemy.orm.session import Session

from manager.database.database import Service, session_scope
from manager.exceptions import (
    DatabaseOutOfSyncException,
    DatabaseConflictException,
    DatabaseNoMatchException,
)

LOGGER = logging.getLogger(__name__)


# pylint: disable=no-member
def get_service_record(session: Session, name: str, version: str) -> Service:
    """Get a service from the service table in a database.

    Args:
        session (Session): Database session.
        name (str): Name of service to get from database.
        version (str): Version of service to get from database.

    Raises:
        DatabaseConflictException: If there exists multiple records matching
            the name and version.
        DatabaseNoMatchException: If there is no service matching the name
            and version specified

    Returns:
        Service: Database record matching the name and version. None if one
            cannot be found.
    """
    service = (
        session.query(Service)
        .filter(and_(Service.name == name, Service.version == version))
        .all()
    )
    if len(service) > 1:
        raise DatabaseConflictException(
            f"Multiple services with same name and version in database: {name}."
        )
    try:
        return service[0]
    except IndexError:
        raise DatabaseNoMatchException(f"No service matching {name} {version}")


def get_main_service_record(session: Session, name: str) -> Service:
    """Get the main service of a certain name from the database.

    Args:
        session (Session): Database session.
        name (str): Name of the service for which to get the main.

    Raises:
        DatabaseConflictException: If there exists multiple main
            services with this name.
        DatabaseNoMatchException: If there is no main service matching
            the specified name.

    Returns:
        Service: Main service with matching name. None if there is
            no matching main service.
    """
    main_service = (
        session.query(Service).filter(and_(Service.name == name, Service.main)).all()
    )
    if len(main_service) > 1:
        raise DatabaseConflictException(
            f"Multiple main {name} services in database: {main_service}."
        )
    try:
        return main_service[0]
    except IndexError:
        raise DatabaseNoMatchException(f"No main service matching {name}")


def add_new_service_record(
    name: str, version: str, image: str, url: str, token_uuid: UUID
) -> bool:
    """Add a new service to the service table of the database. Automatically
    sets main if there are no main services with that same name.

    Args:
        name (str): Name of the new service.
        version (str): Version of the new service.
        image (str): Image of the new service.
        url (str): Url to the new service.
        token_uuid (UUID): The uuid of the auth token for the service.

    Raises:
        DatabaseConflictException: Raised if there already exists a service
            in the database with the same name and version.
    """
    with session_scope() as session:
        # Check if there already exists a main service
        try:
            get_main_service_record(session, name)
            main = False
        except DatabaseNoMatchException:
            main = True

        try:
            get_service_record(session, name, version)
        except DatabaseNoMatchException:
            service = Service(
                name=name,
                version=version,
                image=image,
                url=url,
                main=main,
                token_uuid=token_uuid,
            )
            session.add(service)
        else:
            raise DatabaseConflictException(
                f"Service {name}, {version} already in database."
            )


def delete_service_record(name: str, version: str) -> bool:
    """Deletes a service record from the database matching the name and version.

    Args:
        name (str): Name of the service to remove.
        version (str): Version of the service to remove.

    """
    with session_scope() as session:
        service = get_service_record(session, name, version)
        session.delete(service)


def get_main_and_shadow_versions(name: str) -> Tuple[str, List[str]]:
    """Get the main and shadow versions of services sharing a common name.
        Tries to assign a service to main if no main can be found.

    Args:
        name (str): Name of the service.

    Returns:
        Tuple[str, List[str]]: Main service version and list of shadow versions.
            Defaults to `(None, [])` if there are no matching services
    """
    with session_scope() as session:
        try:
            main_service = get_main_service_record(session, name)
            main_version = main_service.version
        except DatabaseNoMatchException:
            main_version = None

        shadow_services = (
            session.query(Service)
            .filter(and_(Service.name == name, not_(Service.main)))
            .all()
        )
        shadow_versions = [shadow.version for shadow in shadow_services]

    return main_version, shadow_versions


def assign_main_version(name: str, new_main_version: str) -> bool:
    """Assign the main service status to a new service.

    Args:
        name (str): Name of the services for which to change main.
        new_main_version (str): Version of the new main service.

    """
    with session_scope() as session:
        old_main_service = get_main_service_record(session, name)
        new_main_service = get_service_record(session, name, new_main_version)

        old_main_service.main = False
        new_main_service.main = True
        LOGGER.info(f"Changed {name} main service to version {new_main_version}")


def get_all_services_db() -> List[dict]:
    """Get all services in the database as a list of dictionaries.

    Returns:
        List[dict]: All services in the database.
    """
    with session_scope() as session:
        services = session.query(Service).all()
        services_dict = [service.as_dict() for service in services]
    return services_dict


def compare_runtime_db(runtime_services: List[str], db_services: List[dict]):
    """Compares if the runtime and database are synced given a list of
        runtime services (container) names and list of database services.

    Args:
        runtime_services (List[str]): Service container names.
        db_services (List[str]): Database services as dictionaries.

    Raises:
        DatabaseOutOfSyncException: Raised if runtime environment contains
            service(s) that are not present in the database.
        DatabaseOutOfSyncException: Raised if database contains service(s)
            that are not present in the runtime environment.
    """
    runtime_services = {tuple(service.split("-")[-2:]) for service in runtime_services}
    db_services = {(service["name"], service["version"]) for service in db_services}

    extra = runtime_services.difference(db_services)
    missing = db_services.difference(runtime_services)

    if len(extra) > 0:
        raise DatabaseOutOfSyncException(
            "Runtime environment contains service(s) that are not in the"
            f" database: {extra}."
        )
    if len(missing) > 0:
        raise DatabaseOutOfSyncException(
            "Runtime environment missing service(s) present in database:"
            f" {missing}."
            " Please re-deploy the missing service(s) to regain normal function."
        )
