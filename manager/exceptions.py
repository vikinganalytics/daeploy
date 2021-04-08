class S2iException(Exception):
    pass


class TraefikError(Exception):
    """Exception raised if problems in relation to Traefik proxy"""


class DatabaseOutOfSyncException(Exception):
    """Raised if database is out of sync with runtime environment"""


class DatabaseConflictException(Exception):
    """Raised on conflicts of multiple services with the same name
    and version in the database."""


class DatabaseNoMatchException(Exception):
    """Raised when there are not matches for a database query"""
