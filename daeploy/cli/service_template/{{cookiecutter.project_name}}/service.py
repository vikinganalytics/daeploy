import logging
from daeploy import service

logger = logging.getLogger(__name__)

service.add_parameter("greeting_phrase", "Hello")


@service.entrypoint
def hello(name: str) -> str:
    greeting_phrase = service.get_parameter("greeting_phrase")
    logger.info(f"Greeting someone with the name: {name}")
    return f"{greeting_phrase} {name}"


if __name__ == "__main__":
    service.run()
