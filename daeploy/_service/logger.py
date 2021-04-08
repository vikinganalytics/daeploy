import logging
import sys

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("cookiecutter").setLevel(logging.WARNING)
logging.getLogger("binaryornot").setLevel(logging.WARNING)


def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    logging.getLogger("daeploy").setLevel(logging.WARNING)

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
