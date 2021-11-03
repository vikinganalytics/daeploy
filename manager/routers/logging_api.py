from datetime import datetime, timedelta
import logging
import sys
from typing import Union
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from manager.constants import log_level, access_logs_enabled
from manager.runtime_connectors import RTE_CONN

ROUTER = APIRouter()


@ROUTER.get("/", response_class=PlainTextResponse)
async def manager_logs(since: Union[datetime, None] = None) -> str:
    """Get the manager logs since some timestep

    \f
    Args:
        since (datetime, optional): Time to get the first logs. Defaults to None,
            in which case the logs from the last 7 days are returned.

    Raises:
        HTTPException: If there is no running manager container

    Returns:
        str: Manager logs
    """
    since = since or datetime.now() - timedelta(days=7)

    try:
        logs = RTE_CONN.manager_logs(since)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return logs


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level())

    # Turn of logging for everything related to the dashboard
    logging.getLogger("uvicorn.access").addFilter(
        lambda record: "/dashboard/" not in record.getMessage()
    )

    # Turn off logging for GET requests to /auth/verify
    logging.getLogger("uvicorn.access").addFilter(
        lambda record: "GET /auth/verify" not in record.getMessage()
    )

    # Optionally disable access logs completely
    if not access_logs_enabled():
        logging.getLogger("uvicorn.access").setLevel("ERROR")

    formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s - %(name)s - %(message)s"
    )
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
