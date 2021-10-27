from uuid import UUID
from typing import List
from datetime import datetime

import bcrypt
from sqlalchemy.orm.exc import NoResultFound

from manager.exceptions import DatabaseNoMatchException
from manager.database.database import Token, User, session_scope


# pylint: disable=no-member
def add_user_record(username: str, password: str):
    """Add a new user to the database

    Args:
        username (str): Username of new user
        password (str): encrypted password of new user
    """
    with session_scope() as session:
        new_user = User(
            name=username, password=bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        )
        session.add(new_user)


def get_user_record(username: str) -> User:
    """Get the user record for user with 'username'

    Args:
        username (str): Username of user to be fetched

    Raises:
        DatabaseNoMatchException: If no such token can be found

    Returns:
        User: User record if exists else None
    """
    with session_scope() as session:
        try:
            record = session.query(User).filter_by(name=username).one()
        except NoResultFound as exc:
            raise DatabaseNoMatchException from exc
        session.expunge_all()  # Detach record(s) from session
        return record


def get_all_users() -> List[str]:
    """Get a list of all registered users

    Returns:
        List[str]: List of usernames
    """
    with session_scope() as session:
        records = session.query(User.name)
        session.expunge_all()  # Detach record(s) from session
        return [record[0] for record in records]


def delete_user_record(username: str):
    """Delete a user from the database

    Args:
        username (str): Username of of user to be deleted

    Raises:
        DatabaseNoMatchException: Raised if username cannot be found
    """
    with session_scope() as session:
        try:
            record = session.query(User).filter_by(name=username).one()
        except NoResultFound as exc:
            raise DatabaseNoMatchException from exc
        session.delete(record)


def add_token_record(uuid: UUID):
    """Add a new token to the database

    Args:
        uuid (UUID): Unique id of the new token
    """
    with session_scope() as session:
        new_token = Token(uuid=str(uuid), created_at=datetime.utcnow())
        session.add(new_token)


def delete_token_record(uuid: UUID):
    """Delete a token from the database

    Args:
        uuid (UUID): Unique id of the token to be deleted

    Raises:
        DatabaseNoMatchException: If no such token can be found
    """
    with session_scope() as session:
        try:
            record = session.query(Token).filter_by(uuid=str(uuid)).one()
        except NoResultFound as exc:
            raise DatabaseNoMatchException from exc
        session.delete(record)


def get_all_token_records() -> List[Token]:
    """Get all token records from the database

    Returns:
        List[Token]: List of tokens
    """
    with session_scope() as session:
        records = session.query(Token).all()
        session.expunge_all()
        for record in records:
            record.uuid = UUID(record.uuid)
        return records


def get_token_record(uuid: UUID) -> Token:
    """Get the token record for token with 'uuid'

    Args:
        uuid (UUID): UUID of token to be fetched

    Raises:
        DatabaseNoMatchException: If no such token can be found

    Returns:
        Token: Token record
    """
    with session_scope() as session:
        try:
            record = session.query(Token).filter_by(uuid=str(uuid)).one()
        except NoResultFound as exc:
            raise DatabaseNoMatchException from exc

        session.expunge_all()  # Detach record(s) from session
        record.uuid = UUID(record.uuid)
        return record
