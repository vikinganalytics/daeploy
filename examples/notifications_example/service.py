import logging
from daeploy import service
from daeploy.communication import notify, Severity
from daeploy.exceptions import HTTPException

logger = logging.getLogger(__name__)


@service.entrypoint
def hello(name: str) -> str:
    if name.lower() == "world":
        message = "Trying to greet world. Too time consuming!"
        notify(msg=message, severity=Severity.WARNING)
        raise HTTPException(403, detail=message)

    logger.info(f"Greeting someone with the name: {name}")
    return f"Hello {name}"


if __name__ == "__main__":
    service.run()
