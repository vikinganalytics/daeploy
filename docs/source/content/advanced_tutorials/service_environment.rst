.. _service-environment-reference:

Service Environment
===================

A folder `.s2i` is created containing the file `environment` when running ``daeploy init``. By default, it only contains a single row::

    APP_FILE = service.py

This tells `Source-To-Image`, which is used internally to convert code
into a deployable container image, that `service.py` is the main file of the
service. It just defines an environment variable called APP_FILE, like you
would do in linux with:

>>> export APP_FILE=service.py  # doctest: +SKIP

By setting environment variables this way you can add configuration for your
services without having to make changes in the code. To read environment variables
in the service code you can use the
`os module <https://docs.python.org/3/library/os.html>`_
available in standard python::

    import os

    envvar = os.environ.get("ENV_VAR")

Setting Environment Variables at Deployment
-------------------------------------------

It is possible to set environment variables at deployment time using the CLI.
It can be very convenient for deployment specific configuration. Check the 
:ref:`cli-deploy-reference` section to read more.

Daeploy Service Configuration
-----------------------------

There are some special environment variables that are used for Daeploy service
configuration:

    * DAEPLOY_SERVICE_DB_TABLE_LIMIT
        * Number of rows or length of time to keep data in database, cleaned at even intervals. Format ``<number><unit>``. Unit options: ``"rows"``, ``"days"``, ``"hours"``, ``"minutes"`` or ``"seconds"``.
        * Example: ``DAEPLOY_SERVICE_DB_TABLE_LIMIT=30days``

    * DAEPLOY_SERVICE_DB_CLEAN_INTERVAL
        * Interval between database cleans. Format ``<number><unit>``. Unit options: ``"days"``, ``"hours"``, ``"minutes"`` or ``"seconds"``
        * Example: ``DAEPLOY_SERVICE_DB_CLEAN_INTERVAL=7days``