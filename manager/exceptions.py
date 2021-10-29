class DaeployException(Exception):
    """Base exception class for Daeploy manager"""


class S2iException(DaeployException):
    pass


class TraefikError(DaeployException):
    """Exception raised if problems in relation to Traefik proxy"""


class DatabaseOutOfSyncException(DaeployException):
    """Raised if database is out of sync with runtime environment"""


class DatabaseConflictException(DaeployException):
    """Raised on conflicts of multiple services with the same name
    and version in the database."""


class DatabaseNoMatchException(DaeployException):
    """Raised when there are no matches for a database query"""


class DeploymentError(DaeployException):
    """Raised when there is an exception with deployment"""
