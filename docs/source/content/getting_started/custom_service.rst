.. _custom-service-reference:

Anatomy of a Service
====================

In this tutorial we will go through the code of the service that is generated
by ``daeploy init`` to learn the parts that make up a Daeploy service.

>>> daeploy init # doctest: +SKIP
project_name [my_project]: my_first_daeploy_project
>>> ls ./my_first_daeploy_project -a # doctest: +SKIP
.  ..  .s2i/  .s2iignore  README.md  requirements.txt  service.py  tests/

`service.py` contains the service code, `requirements.txt` contains any dependencies
of `service.py` and `.s2i/` contains a file that defines environment variables.
To create a service with the Daeploy SDK, only these three files are strictly
required. The remaining files serve other purposes and we touch on them in later
tutorials.

Let's take a look at the contents of `service.py` to see how the SDK is used to
create the service.

Setup
-----

The first step is to import packages. We also initialize a logger
so we can get information about the service for debugging:

.. testcode::

    import logging
    from daeploy import service

    logger = logging.getLogger(__name__)

Only :py:obj:`service` is actually required, but we recommend to import
and use the standard python `logging <https://docs.python.org/3/library/logging.html>`_ 
package.

If any external packages are used, they must be specified in the `requirements.txt` file. 
That way they will be installed the service is deployed. 

.. note:: It is highly recommended to **pin** your requirements to specific versions when 
    in a production environment, for example `numpy==1.19.4`

The :py:obj:`service` object helps us set up entrypoints for the service,
add parameters and start the service. The logger is just a regular python logging
object, which Daeploy natively supports. The logs from a service can be read from the
dashboard or using ``daeploy logs name version``.

.. _custom-service_defining_parameters-reference:

Defining parameters
-------------------

It is possible to define parameters that automatically get exposed to the API and
can be freely changed from outside a running service

.. testcode::
    
    service.add_parameter("greeting_phrase", "Hello")
    

Get the value of a parameter with

.. testcode::

    greeting_phrase = service.get_parameter("greeting_phrase")


This way you can control the behaviour of your running services without having
to make any code changes. We recommend using them for control parameters.

Creating an Entrypoint
----------------------

To define an entrypoint for a service we use the :py:obj:`~daeploy.service.entrypoint` decorator

.. testcode::

    @service.entrypoint
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        logger.info(f"Greeting someone with the name: {name}")
        return f"{greeting_phrase} {name}"

This will automatically expose the :py:func:`hello` function to the API. We strongly
recommend that you use type hints in your Daeploy entrypoint functions. That way, you
will get type verification in your API and the auto-generated documentation will show
the expected data types. Please take a look at :ref:`sdk-typing-reference` for a
more detailed guide on how typing is handled in Daeploy.

.. note:: Daeploy entrypoints should have JSON-compatible data as input and output. Note that e.g.
    ``numpy.ndarray`` and ``pandas.DataFrame`` are not JSON-compatible and must be converted to
    lists or dictionaries. Read :ref:`sdk-typing-non-json-reference` on how to use such data types.

Starting the Service
--------------------

The last thing we have to do is to ensure the service runs once it is deployed

.. testcode::

    if __name__ == '__main__':
        service.run()


Full Code
---------

All together the full service contains fewer than 25 lines of code, including input
validation, logging and configurable parameters:

.. testcode::

    import logging
    from daeploy import service

    logger = logging.getLogger(__name__)

    service.add_parameter("greeting_phrase", "Hello")

    @service.entrypoint
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        logger.info(f"Greeting someone with the name: {name}")
        return f"{greeting_phrase} {name}"


    if __name__ == '__main__':
        service.run()

Deploying the Service
---------------------

With the service code in place we can deploy it with:

>>> daeploy deploy hello 1.0.0 ./my_first_daeploy_project/ # doctest: +SKIP
Deploying service...
Service deployed successfully
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
*       hello   1.0.0      running   Running (since 2020-11-23 10:29:01)

What's Next?
------------

Now you have seen the different components of the SDK and you should be ready to
create your own service. The next step could be to take a look at the
manager :ref:`dashboard-reference`, or the :ref:`sdk-reference` documentation.
