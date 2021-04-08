import logging
from daeploy import service
from random import randint

logger = logging.getLogger(__name__)


@service.entrypoint
def roll_die() -> int:
    return randint(1, 6)


if __name__ == "__main__":
    service.run()
