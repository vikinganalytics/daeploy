from datetime import datetime, timedelta
import logging
import sys
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from manager.constants import log_level, access_logs_enabled, get_manager_version
from manager.runtime_connectors import RTE_CONN

ROUTER = APIRouter()

TEMPLATES = Jinja2Templates(directory="manager/templates")


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


@ROUTER.get("/stream", response_class=StreamingResponse)
async def manager_logs_stream(
    tail: Optional[int] = None,
    follow: Optional[bool] = False,
    since: Union[datetime, None] = None,
) -> str:
    """Stream the manager logs (optionally following new output).

    \f
    # noqa: DAR101,DAR201
    """
    return StreamingResponse(
        RTE_CONN.manager_logs_stream(tail, follow, since),
        media_type="text/plain",
        headers={"X-Content-Type-Options": "nosniff"},
    )


@ROUTER.get("/view", response_class=HTMLResponse)
def manager_logs_view(request: Request):
    """HTML view that streams the manager logs with a follow/auto-scroll toggle.

    \f
    # noqa: DAR101,DAR201
    """
    return TEMPLATES.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "title": "manager",
            "subtitle": f"v: {get_manager_version()}",
            "stream_url": "/logs/stream?follow=true&tail=400",
            "full_url": "/logs/stream?tail=all",
            "export_basename": "manager",
            "manager_version": get_manager_version(),
        },
    )


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
