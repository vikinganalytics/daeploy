import logging

from daeploy import service
from daeploy.exceptions import HTTPException

logger = logging.getLogger(__name__)

STORAGE_DICTS = dict()


@service.entrypoint(status_code=201)
def create_new_dict(dict_name: str, content: dict):

    if STORAGE_DICTS.get(dict_name, False):
        raise HTTPException(status_code=409, detail=f"{dict_name} already exists")

    STORAGE_DICTS[dict_name] = content
    return "Created"


@service.entrypoint()
def get_dict(dict_name: str):
    return STORAGE_DICTS[dict_name]


if __name__ == "__main__":
    service.run()
