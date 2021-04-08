# pylint: disable=global-statement
import queue
import logging
import threading
import datetime
from pathlib import Path
from typing import Union, Type, List
from contextlib import contextmanager
import json

from sqlalchemy import create_engine, and_, event, DDL
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker, mapper, clear_mappers
from sqlalchemy import Column, DateTime, Float, Text

from daeploy.utilities import get_db_table_limit

LOGGER = logging.getLogger(__name__)

SERVICE_DB_PATH = Path("service_db.db")

ENGINE = create_engine(f"sqlite:///{str(SERVICE_DB_PATH)}")
Base = automap_base()
Session = sessionmaker(bind=ENGINE)

QUEUE = queue.Queue()
TABLES = {}
LOCK = threading.Lock()

ROW_TRIGGER = """\
CREATE TRIGGER {name}_limit_n_rows AFTER INSERT ON {name}
BEGIN
    DELETE FROM {name} WHERE timestamp NOT IN
        (SELECT timestamp FROM {name} ORDER BY timestamp DESC LIMIT {n_rows});
END"""

TIME_TRIGGER = """\
CREATE TRIGGER {name}_delete_old_records AFTER INSERT ON {name}
BEGIN
    DELETE FROM {name}
    WHERE DATETIME(timestamp) < DATETIME('now', '-{duration} {timescale}');
END"""


def create_new_ts_table(name: str, dtype: Type) -> Type:
    """Create a new timeseries table in the db

    Args:
        name (str): Name of the variable to be stored in the table
        dtype (Type): Type of the variable to be stored in the table,
            can be any of float and str

    Raises:
        TypeError: If dtype is not one of float or str

    Returns:
        Type: Newly created mapped type
    """
    # Find correct SQL type to use
    if dtype == float:
        sql_type = Float
    elif dtype == str:
        sql_type = Text
    else:
        raise TypeError(
            f"Monitored variable {name} is of an unacceptable type: {dtype} "
            "and will not be stored! Has to be one of float|str."
        )

    # Create table mapper class
    MapperClass = type(  # pylint: disable=invalid-name
        name.capitalize(),
        (Base,),
        {
            "__tablename__": name,
            "timestamp": Column(
                DateTime, primary_key=True, index=True, default=datetime.datetime.utcnow
            ),
            "value": Column(sql_type),
        },
    )

    # Create a trigger for deleting old values in tables
    limit, limiter = get_db_table_limit()
    if limiter == "rows":
        table_limit_trigger = DDL(ROW_TRIGGER.format(name=name, n_rows=limit))
    else:
        table_limit_trigger = DDL(
            TIME_TRIGGER.format(name=name, duration=limit, timescale=limiter)
        )
    event.listen(MapperClass.__table__, "after_create", table_limit_trigger)

    # Create the actual table
    MapperClass.__table__.create(ENGINE, checkfirst=True)

    # Map everything
    mapper(MapperClass, MapperClass.__table__)

    LOGGER.info(f"Created new table for variable {name}")

    return MapperClass


# pylint: disable=no-member
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


# pylint: disable=no-member
def _writer():
    """Writer thread function"""
    while True:
        # Get next value from queue
        item = QUEUE.get()
        if not item:
            # Time to shut down
            break

        name, value, timestamp = item

        # Create table if not exists and get mapped class
        try:
            # Try to save as json strings if value is not a string or number
            if not isinstance(value, (float, str)):
                value = json.dumps(value)

            if name not in TABLES:
                with LOCK:
                    TABLES[name] = create_new_ts_table(name, type(value))
            item = TABLES[name](timestamp=timestamp, value=value)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(str(exc))
            continue

        # Write value to table!
        try:
            with LOCK, session_scope() as session:
                session.add(item)
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Write to db failed!")

        QUEUE.task_done()


WRITER_THREAD = threading.Thread(target=_writer, daemon=True)


def write_to_ts(name: str, value: Union[float, str], timestamp: datetime.datetime):
    """Write a value to the timeseries identified by name

    Args:
        name (str): Identifier of timeserie
        value (Union[float, str]): Value to be written
        timestamp (datetime.datetime): Timestamp for measurment
    """
    QUEUE.put((name, value, timestamp))


def stored_variables() -> List[str]:
    """Returns a list of the variables that are currently being stored in the db

    Returns:
        List[str]: List of variables names.
    """
    return list(TABLES.keys())


# pylint: disable=no-member
def read_from_ts(
    name: str, from_time: datetime.datetime = None, to_time: datetime.datetime = None
) -> List:
    """Read from a specific timeseries

    Args:
        name (str): Identifier of timeseries to read from
        from_time (datetime.datetime): Read values starting from this
            point in time. Defaults to None.
        to_time (datetime.datetime): Read values up to this point in time.
             Defaults to None.

    Raises:
        ValueError: If a variable with identifier `name` can not
             be found in the database

    Returns:
        List: A list of results
    """
    if name not in TABLES:
        raise ValueError(f"Timeseries with identifier {name} does not exist!")

    from_time = from_time or datetime.datetime.min
    to_time = to_time or datetime.datetime.utcnow()

    Item = TABLES[name]  # pylint: disable=invalid-name

    with session_scope() as session:
        records = (
            session.query(Item)
            .filter(and_(Item.timestamp >= from_time, Item.timestamp <= to_time))
            .all()
        )
        session.expunge_all()  # Detach record(s) from session
        return records


def initialize_db():
    """Initializes the database."""
    global TABLES
    Base.prepare(ENGINE, reflect=True)  # Automap any existing tables
    TABLES = dict(Base.classes)  # Make sure we keep track of the auto-mapped tables
    WRITER_THREAD.start()
    LOGGER.info("DB started!")


def remove_db():
    """Remove db"""
    global WRITER_THREAD

    # Stop and join writer thread if alive
    if WRITER_THREAD.is_alive():
        QUEUE.put(None)  # Signal shutdown to writer thread
        WRITER_THREAD.join()

    # Reset it
    WRITER_THREAD = threading.Thread(target=_writer, daemon=True)

    # Remove db
    SERVICE_DB_PATH.unlink()

    # Reset mappers and metadata object
    clear_mappers()
    Base.metadata.clear()
    LOGGER.info("DB has been shut down!")
