.. _log-reference:

Read Logs From Service
======================

You are able to read anything that your service writes to stdout (for example using
the python logging package or ``print``) from outside the service. The logs are streamed
to the Manager dashboard and can be read with the CLI: 

>>> daeploy logs my_service # doctest: +SKIP

To stream the logs to the CLI:

>>> daeploy logs --follow  my_service  # doctest: +SKIP

Options for Reading the Logs Using the CLI
------------------------------------------

There are a few options that can be passed to the ``logs`` command to make reading the logs a bit more pleasant. 

- ``-n`` , ``--tail``: Return the latest `n` logs [default: 50]  
- ``-f``, ``--follow``: If the logs should be followed [default: False]
- ``-d``, ``--date``: Show logs since given datetime.

.. tip:: ``daeploy logs`` is compatible with ``grep`` so to filter on logs containing ``WARNING`` one can run the following:
    
    >>> daeploy logs my_service --follow | grep WARNING # doctest: +SKIP

    Or if using powershell on windows:

    >>> daeploy logs my_service --follow | findstr WARNING # doctest: +SKIP