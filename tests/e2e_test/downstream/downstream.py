"""
File used as a service in e2e tests.
"""
import logging
import time
from pydantic import BaseModel

from daeploy import service
from daeploy.communication import notify, Severity

logging.getLogger("daeploy").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

service.add_parameter("greeting_phrase", "Hello")


@service.entrypoint
def hello(name: str) -> str:
    greeting_phrase = service.get_parameter("greeting_phrase")
    logger.info(f"Greeting someone with the name: {name}")
    return f"{greeting_phrase} {name}"


@service.entrypoint
def raise_notification() -> str:
    notify(msg="Notification raised...", severity=Severity.WARNING, emails=None)
    return "Done"


@service.entrypoint(method="GET")
def get_method() -> str:
    return "Get - Got - Gotten"


class model1(BaseModel):
    name: str
    sirname: str


class model2(BaseModel):
    age: int
    height: int


class model3(BaseModel):
    name: str
    sirname: str
    age: int
    height: int


@service.entrypoint
def function_with_basemodel_args(name: model1, info: model2) -> model3:
    return {
        "name": name.name,
        "sirname": name.sirname,
        "age": info.age,
        "height": info.height,
    }


@service.entrypoint
def store_variables_10_times():
    for i in range(10):
        time.sleep(0.1)
        service.store(v1=i, v2=i * 2)


@service.entrypoint
def store_variable_vz_10_times():
    for i in range(10):
        time.sleep(0.1)
        service.store(vz=i)


@service.entrypoint(disable_http_logs=True)
def http_logs():
    logger.info("This is a correct log!")


@service.entrypoint(disable_http_logs=False)
def http_logs_2():
    pass


if __name__ == "__main__":
    service.run()
