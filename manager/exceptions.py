class S2iException(Exception):
    """Raised if there has been an error with source to image"""


class AuthError(Exception):
    """Exception raised on authorization and authentication errors"""


class TraefikError(Exception):
    """Exception raised if problems in relation to Traefik proxy"""


class DatabaseOutOfSyncException(Exception):
    """Raised if database is out of sync with runtime environment"""


class DatabaseConflictException(Exception):
    """Raised on conflicts of multiple services with the same name
    and version in the database."""


class DatabaseNoMatchException(Exception):
    """Raised when there are no matches for a database query"""
