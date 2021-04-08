import warnings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from manager.database.database import Config, session_scope
from manager.exceptions import DatabaseNoMatchException


# pylint: disable=no-member
def add_config_record(key: str, value: str):
    """Add a new config key-value pair to the db

    Args:
        key (str): Key of key-value pair
        value (str): Value of key-value pair
    """

    with session_scope() as session:
        new_config = Config(key=key, value=value)
        session.add(new_config)


def get_config_record(key: str) -> Config:
    """Get the config record associated with 'key'

    Args:
        key (str): Key to filter by

    Raises:
        DatabaseNoMatchException: If no such token can be found

    Returns:
        Config: Fetched Config record if exists else None
    """
    with session_scope() as session:
        try:
            record = session.query(Config).filter_by(key=key).one()
        except NoResultFound as exc:
            raise DatabaseNoMatchException from exc
        session.expunge_all()  # Detach record(s) from session
        return record


def set_jwt_token_secret(secret: str):
    """Sets a new token secret if not already set

    Args:
        secret (str): secret to set
    """
    try:
        add_config_record("JWT_TOKEN_SECRET", secret)
    except IntegrityError:
        warnings.warn("JWT TOKEN SECRET already set!", UserWarning)


def get_jwt_token_secret() -> str:
    """Gets the current token secret from database

    Returns:
        str: Secret
    """
    record = get_config_record("JWT_TOKEN_SECRET")
    return record.value
