import logging
from daeploy import service

logger = logging.getLogger(__name__)

@service.entrypoint
def hello(name: str) -> str:
    logger.info(f"Greeting someone with the name: {name}")
    return f"Hello {name}"


if __name__ == "__main__":
    service.run()
