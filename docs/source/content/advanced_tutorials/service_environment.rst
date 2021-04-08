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

Daeploy Service Configuration
-----------------------------

There are some special environment variables that are used for Daeploy service
configuration.

.. list-table::
   :widths: 25 25 25
   :header-rows: 1

   * - Environment Variable
     - Explanation
     - Example
   * - ``DAEPLOY_SERVICE_DB_TABLE_LIMIT``
     - Format ``<number><limiter>``. Limiter options: ``"rows"``, ``"days"``, ``"hours"``, ``"minutes"`` or ``"seconds"``.
     - ``DAEPLOY_SERVICE_DB_TABLE_LIMIT=30days``
