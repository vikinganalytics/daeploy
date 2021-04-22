import asyncio
import datetime
import functools
import inspect
from inspect import Parameter
import logging
import time
import warnings
from typing import Callable, Any
import json
from numbers import Number
import uvicorn
from fastapi import Body, Request, FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.concurrency import run_in_threadpool
from pydantic import create_model, validate_arguments

from daeploy._service.logger import setup_logging
from daeploy._service.db import initialize_db, remove_db, write_to_ts
from daeploy._service.monitoring_api import (
    get_monitored_data_json,
    get_monitored_data_db,
    get_monitored_data_csv,
)
from daeploy.utilities import (
    get_service_name,
    get_service_version,
    get_service_root_path,
    HTTP_METHODS,
)

setup_logging()
logger = logging.getLogger(__name__)


class _Service:
    def __init__(self):
        self.app = FastAPI(
            root_path=get_service_root_path(),
            title=f"{get_service_name()} {get_service_version()}",
            description="Automatically generated, interactive API documentation",
            openapi_tags=[
                {"name": "Entrypoints"},
                {"name": "Monitoring"},
                {"name": "Parameters"},
            ],
        )

        self.parameters = {}

        # daeploy-specific setup
        self.app.on_event("startup")(initialize_db)
        self.app.on_event("shutdown")(service_shutdown)

        # Monitoring API
        self.app.get("/~monitor", tags=["Monitoring"])(get_monitored_data_json)
        self.app.get("/~monitor/csv", tags=["Monitoring"])(get_monitored_data_csv)
        self.app.get("/~monitor/db", tags=["Monitoring"])(get_monitored_data_db)

        # Parameters API
        def get_all_parameters() -> dict:
            """Get all registered parameter endpoints

            \f
            Returns:
                dict: The registered parameters and their current value
            """
            return {
                param: param_dict["value"]
                for param, param_dict in self.parameters.items()
            }

        self.app.get("/~parameters", tags=["Parameters"])(get_all_parameters)

    def entrypoint(
        self,
        func: Callable = None,
        method: str = "POST",
        monitor: bool = False,
        disable_http_logs: bool = False,
        **fastapi_kwargs,
    ) -> Callable:
        """Registers a function as an entrypoint, which will make it reachable
        as an HTTP method on your host machine.

        Decorate a function with this method to create an entrypoint for it::

            @entrypoint
            def my_function(arg1:type1) -> type2:
                ....

        It is strongly recommended to include types of the arguments and return
        objects for the decorated function.

        Args:
            func (Callable): The decorated function to make an entrypoint for.
            method (str): HTTP method for entrypoint. Defauts to "POST"
            monitor (bool): Set if the input and output to this entrypoint should
                be saved to the service's monitoring database. Defaults to False.
            disable_http_logs (bool): Set if the http entry logs should be disabled for
                this entrypoint.
                These logs are genereated from uvicorn. Defaults to False.
                Example of http entry log:
                    "POST /services/service_1.0.0/entrypoint_name HTTP/1.1" 200 OK
            **fastapi_kwargs: Keyword arguments for the resulting API endpoint.
                See FastAPI for keyword arguments of the ``FastAPI.api_route()``
                function.

        Raises:
            TypeError: If :obj:`func` is not callable.
            ValueError: If method is not a valid HTTP method.

        Returns:
            Callable: The decorated function: :obj:`func`.
        """
        method = method.upper()
        if method not in HTTP_METHODS:
            raise ValueError(
                f"Invalid HTTP method: {method}." f" Possible options: {HTTP_METHODS}"
            )

        # pylint: disable=protected-access
        def entrypoint_decorator(deco_func):
            funcname = deco_func.__name__
            path = f"/{funcname}"
            signature = inspect.signature(deco_func)

            # Update default values to fastapi Body parameters to force all parameters
            # in a json body for the resulting HTTP method
            new_params = []
            request_sig = inspect.Parameter(
                "_request", Parameter.POSITIONAL_OR_KEYWORD, annotation=Request
            )
            new_params.append(request_sig)
            for parameter in signature.parameters.values():
                if parameter.default == inspect._empty:
                    default = Ellipsis
                else:
                    default = parameter.default
                new_params.append(parameter.replace(default=Body(default, embed=True)))

            @functools.wraps(deco_func)
            # async is required for the request.body() method.
            async def wrapper(_request: Request, *args, **kwargs):
                result = await run_in_threadpool(deco_func, *args, **kwargs)

                if monitor:
                    request_body = await _request.body()
                    json_response = json.dumps(jsonable_encoder(result))
                    self.store(
                        **{
                            f"{funcname}_request": request_body.decode("utf-8"),
                            f"{funcname}_response": json_response,
                        }
                    )
                return result

            # Update the signature
            signature = signature.replace(parameters=new_params)
            wrapper.__signature__ = signature

            # Get response_model from return type hint
            return_type = signature.return_annotation
            if return_type == inspect._empty:
                return_type = None

            # Give priority to explicitly given response_model
            kwargs = dict(response_model=return_type)
            kwargs.update(fastapi_kwargs)

            # Create API endpoint
            self.app.api_route(path, methods=[method], tags=["Entrypoints"], **kwargs)(
                wrapper
            )

            if disable_http_logs:
                logging.getLogger("uvicorn.access").addFilter(
                    # Add a space to the path to make sure that we
                    # only filter out this entrypoints HTTP logs.
                    lambda record: f"{path} "
                    not in record.getMessage()
                )

            # Wrap the original func in a pydantic validation wrapper and return that
            return validate_arguments(deco_func)

        # This ensures that we can use the decorator with or without arguments
        if not (callable(func) or func is None):
            raise TypeError(f"{func} is not callable.")
        return entrypoint_decorator(func) if callable(func) else entrypoint_decorator

    def store(self, **variables):  # pylint: disable=no-self-use
        """Saves variables to the service's monitoring database. Supports
        numbers and strings. If a variable is not a number or string it store
        will try to coerce it into a string before storing.

        Args:
            **variables: Variables to save to the database. Non-numeric
                variables will be saved as ``str(variable)``.
        """
        timestamp = datetime.datetime.utcnow()
        for variable, value in variables.items():
            if isinstance(value, Number):
                value = float(value)
            write_to_ts(name=variable, value=value, timestamp=timestamp)

    def call_every(
        self,
        seconds: float,
        wait_first: bool = False,
    ):
        """Returns a decorator that converts a function to an awaitable that runs
        every `seconds`.

        Decorate a function with this method to make it run repeatedly::

            @call_every(seconds=60)
            def my_function():
                ....

        Args:
            seconds (float): Interval between calls in seconds
            wait_first (bool): If we should skip the first execution. Defaults to False.

        Returns:
            Callable: The decorator
        """

        def timed_task_decorator(func: Callable) -> Callable:
            """Puts the decorated `func` in a timed asynchronous loop and
            returns the unwrapped `func` again.

            Args:
                func (Callable): The function to be called repeatedly

            Returns:
                Callable: The same function that was inputted
            """
            is_coroutine = asyncio.iscoroutinefunction(func)

            async def timer():

                # Sleep before first call if required
                if wait_first:
                    await asyncio.sleep(seconds)

                # Run forever
                while True:
                    # For timing purposes
                    t_0 = time.time()

                    # Await `func` and log any exceptions
                    try:
                        if is_coroutine:
                            # Non-blocking code, defined by `async def`
                            await func()
                        else:
                            # Blocking code, defined by `def`
                            await run_in_threadpool(func)
                    except Exception:  # pylint: disable=broad-except
                        logger.exception(f"Exception in {func}")

                    # Timing check
                    remainder = seconds - (time.time() - t_0)
                    if remainder < 0:
                        warnings.warn(
                            f"Function {func} has an execution time the exceeds"
                            f" the requested execution interval of {seconds}s!",
                            UserWarning,
                        )

                    # Sleep until next time
                    await asyncio.sleep(max(remainder, 0))

            # Put `timer` on the event loop on service startup
            @self.app.on_event("startup")
            async def _starter():
                asyncio.ensure_future(timer())

            return func

        return timed_task_decorator

    def get_parameter(self, parameter: str) -> Any:
        """Get specific parameter

        Args:
            parameter (str): The name of the parameter

        Returns:
            Any: The value of the parameter
        """
        return self.parameters[parameter]["value"]

    def set_parameter(self, parameter: str, value: Any) -> Any:
        """Change the value of a parameter from inside a service.

        Args:
            parameter (str): The name of the parameter
            value (Any): The new value to assign to the
                parameter. Should be the same type as the previous value.

        Returns:
            Any: The value of the parameter
        """
        setter = self.parameters[parameter]["setter"]
        return setter(value)

    def add_parameter(
        self,
        parameter: str,
        value: Any,
        expose: bool = True,
        monitor: bool = False,
    ):
        """Adds a parameter to the parameter endpoints.

        Args:
            parameter (str): The name of the parameter
            value (Any): The value of the parameter
            expose (bool): Should parameter update be exposed to the API.
                Defaults to True.
            monitor (bool): Stores updates to this parameter in the monitoring
                database if True. Will try to coerce non-numeric types to
                string Defaults to False.
        """
        if isinstance(value, Number):
            value = float(value)

        @validate_arguments()
        def update_parameter(value: value.__class__) -> Any:
            logger.info(f"Parameter {parameter} changed to {value}")
            self.parameters[parameter]["value"] = value
            if monitor:
                self.store(**{parameter: value})
            return value

        # Set initial value
        self.parameters[parameter] = {
            "value": None,
            "setter": update_parameter,
        }
        update_parameter(value)

        # Register GET endpoint for the new parameter
        def get_parameter():
            return self.parameters[parameter]["value"]

        path = f"/~parameters/{parameter}"
        self.app.get(path, tags=["Parameters"])(get_parameter)

        # Register POST endpoint for the new parameter
        if expose:
            update_request_model = create_model(
                f"{parameter}_schema", value=(value.__class__, ...)
            )

            def post_update_parameter(model: update_request_model):
                update_parameter(model.value)
                return "OK"

            self.app.post(path, tags=["Parameters"])(post_update_parameter)

    def run(self):
        """Runs the service

        This method is usually called at the end of the module when all
        entrypoints etc for the service has been specified
        """
        logger.info(f"Service started at: {datetime.datetime.utcnow()}")
        uvicorn.run(self.app, host="0.0.0.0", port=8000)


def service_shutdown():
    """Actions to that should be performed before stopping the service.
    - Logging
    - Removing of database
    """
    remove_db()
    logger.info(f"Service stopped at: {datetime.datetime.utcnow()}")
