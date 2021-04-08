import csv
import tempfile
import shutil
import datetime
import logging

from pathlib import Path
from typing import List, Optional
from fastapi.responses import FileResponse
from fastapi import HTTPException, Query
from daeploy._service.db import read_from_ts, stored_variables, LOCK, SERVICE_DB_PATH

SERVICE_DB_COPY_PATH = Path("service_copy_db.db")

logger = logging.getLogger(__name__)


def get_monitored_data_json(
    start: Optional[datetime.datetime] = Query(None),
    end: Optional[datetime.datetime] = Query(None),
    variables: Optional[List[str]] = Query(None),
) -> dict:
    """Get time-series data for monitored variables in json format.

    \f
    Args:
        start (Optional[datetime.datetime], optional): The start time of the
            requested timeseries. Defaults to None which corresponds to the
            begining of the monitoring.
        end (Optional[datetime.datetime], optional): The end time of the requested
            timeseries. Defaults to None which corresponds to the end of the
            monitoring.
        variables (Optional[List[str]], optional): List of the names of the
            variables to get timeseries data for. Defaults to None which
            corresponds to all monitored variables.

    Raises:
        HTTPException: If variable in 'variables' does not exists.

    Returns:
        dict: The timeseries data for 'variables' as a dictionary.
    """
    variables = variables or stored_variables()
    output = {}

    for variable in variables:
        try:
            entries = read_from_ts(variable, start, end)
        except ValueError as exp:
            raise HTTPException(status_code=412, detail=str(exp))

        output[variable] = {
            "timestamp": [str(entry.timestamp) for entry in entries],
            "value": [entry.value for entry in entries],
        }
    return output


def get_monitored_data_csv(
    start: Optional[datetime.datetime] = Query(None),
    end: Optional[datetime.datetime] = Query(None),
    variables: Optional[List[str]] = Query(None),
) -> FileResponse:
    """Get time-series data for monitored variables as csv files in zip archive.

    \f
    Args:
        start (Optional[datetime.datetime], optional): The start time of the
            requested timeseries. Defaults to None which corresponds to the
            begining of the monitoring.
        end (Optional[datetime.datetime], optional): The end time of the requested
            timeseries. Defaults to None which corresponds to the end of the
            monitoring.
        variables (Optional[List[str]], optional): List of the names of the
            variables to get timeseries data for. Defaults to None which
            corresponds to all monitored variables.

    Raises:
        HTTPException: If no monitored variables exists.

    Returns:
        FileResponse: Response containing zip archive with one csv file per variable
            in 'variables'.
    """
    variables = variables or stored_variables()
    if not variables:
        raise HTTPException(status_code=412, detail="No monitored variables exists")
    with tempfile.TemporaryDirectory() as tmpdirname:
        for variable in variables:
            csv_file_name = f"{tmpdirname}/{variable}.csv"
            variable_data = get_monitored_data_json(
                start=start, end=end, variables=[variable]
            )[variable]

            # Create one csv file per variable.
            with open(csv_file_name, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=["timestamp", "value"])
                writer.writeheader()
                for timestamp, value in zip(*variable_data.values()):
                    writer.writerow({"timestamp": timestamp, "value": value})
                logger.info(
                    f"Created temp csv file of timeseries data for variable {variable}"
                )

        shutil.make_archive(tmpdirname, "zip", tmpdirname)
        logger.info("Created zip of temp directory with csv data files")
        return FileResponse(f"{tmpdirname}.zip", filename="csv_data.zip")


def get_monitored_data_db() -> FileResponse:
    """Get service database file.

    \f

    Raises:
        HTTPException: If failed to make a copy of the db and return it.

    Returns:
        FileResponse: Response containing the database file.
    """
    try:
        with LOCK:
            # As of now we make a copy of the db file which we don't remove.
            # FileResponse cannot handle temp files.
            shutil.copy(SERVICE_DB_PATH, SERVICE_DB_COPY_PATH)
            logger.info(
                f"Copied content from {SERVICE_DB_COPY_PATH} to {SERVICE_DB_COPY_PATH}"
            )
            return FileResponse(path=SERVICE_DB_COPY_PATH, filename="database.db")
    except Exception as exp:
        logger.exception("Failed to copy content from db to copy file.")
        raise HTTPException(status_code=412, detail=str(exp))
