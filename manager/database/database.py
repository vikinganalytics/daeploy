import os
from base64 import b64encode
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

from manager.constants import DAEPLOY_DATA_DIR, get_admin_password

MANAGER_DB_PATH = DAEPLOY_DATA_DIR / "daeploy_manager_db.db"

logger = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{str(MANAGER_DB_PATH)}")
Base = declarative_base()
Session = sessionmaker(bind=engine)


# pylint: disable=no-member
class Service(Base):
    """Service schema for SQLite database table."""

    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    version = Column(String)
    image = Column(String)
    url = Column(String)
    main = Column(Boolean)
    token_uuid = Column(String, ForeignKey("tokens.uuid"))

    def __repr__(self) -> str:
        """Printable representation of service record.

        Returns:
            str: String representation.
        """
        return (
            f"<Service(name={self.name}, version={self.version}, "
            f"url={self.url}, main={self.main}, token_uuid={self.token_uuid})>"
        )

    def as_dict(self) -> dict:
        """Get a service record as a dictionary.

        Returns:
            dict: Service record.
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Config(Base):
    """Schema emulating a key-value store for config that should
    survive restarts.
    """

    __tablename__ = "config"

    key = Column(String, primary_key=True, unique=True)
    value = Column(String)


class Token(Base):
    """Schema for storing long-lived API tokens"""

    __tablename__ = "tokens"

    uuid = Column(String, primary_key=True)
    created_at = Column(DateTime)


class User(Base):
    """Schema for storing users."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    password = Column(String)


@contextmanager
def session_scope() -> Session:
    """Define a database session.

    Raises:
        Exception: Exception that occurs during the session.

    Yields:
        Session: Database session.
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        raise exc
    finally:
        session.close()


# pylint: disable=import-outside-toplevel, cyclic-import
def initialize_db():
    """Initializes the database."""
    Base.metadata.create_all(engine)

    # Try adding a token secret
    from manager.database.config_db import set_jwt_token_secret

    set_jwt_token_secret(b64encode(os.urandom(64)).decode())

    # Add our base set of users
    from manager.database.auth_db import add_user_record, clear_user_database

    clear_user_database()
    add_user_record(username="admin", password=get_admin_password())


def remove_db():
    """Removes db"""
    try:
        MANAGER_DB_PATH.unlink()
    except FileNotFoundError:
        # Path.unlink(missing_ok=True) gives same behavior but was
        # not introduced until python 3.8
        pass
