.. _monitoring-reference:

Monitoring Your Service
=======================

Monitoring is a very important aspect of software deployment. Deployed algorithms
often deteriorate over time, in a process called 
`domain shift <https://en.wikipedia.org/wiki/Domain_adaptation>`_, and being able
to monitor your deployed algorithms can make all the difference in detecting this
in the early stages.

Monitoring Variables
--------------------

To monitor the value of a variable in the code you can use the
:py:func:`~daeploy.service.store` function. It takes an arbitrary number of keyword
arguments and saves their values in a service-specific database, where they can be
retrieved at a later time. :py:func:`~daeploy.service.store` supports numeric and
string data. Let's use the `hello` service as an example

.. testcode::

    import logging
    from daeploy import service
    
    logger = logging.getLogger(__name__)

    service.add_parameter("greeting_phrase", "Hello")

    @service.entrypoint
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        logger.info(f"Greeting someone with the name: {name}")
        
        # Now the name and greeting will be stored everytime this function is called
        service.store(name=name, greeting=greeting_phrase)

        return f"{greeting_phrase} {name}"

Monitoring an Entrypoint
------------------------

It is also possible to automatically monitor the input and output of a service
entrypoint. To do this we pass ``monitor=True`` to the 
:py:meth:`~daeploy.service.entrypoint` decorator

.. testcode::

    import logging
    from daeploy import service

    logger = logging.getLogger(__name__)

    service.add_parameter("greeting_phrase", "Hello")

    # Now the input and output of this entrypoint is stored after each call 
    @service.entrypoint(monitor=True)
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        logger.info(f"Greeting someone with the name: {name}")
        return f"{greeting_phrase} {name}"

In this case, the data is saved as json strings, in order to support more data
formats.

Monitoring a Parameter
----------------------

Parameters set with :py:func:`~daeploy.service.add_parameter` can also be monitored by passing
``monitor=True``, which also supports integer, float and string data

.. testcode::

    import logging
    from daeploy import service

    logger = logging.getLogger(__name__)

    # Now the value of ``"greeting_phrase"`` is stored every time it's updated
    service.add_parameter("greeting_phrase", "Hello", monitor=True)

    @service.entrypoint
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        logger.info(f"Greeting someone with the name: {name}")
        return f"{greeting_phrase} {name}"

Getting the Data
----------------

Daeploy provides three options for accessing the time-series data for
your monitored variables.

**Option 1: Json format**

The time-series data in json format can be collected via the following entrypoint:

``http://your-host/services/<servce_name>_<service_version>/~monitor``

It is possible to specify start time and end time for the wanted time-series data by adding
`end` and `start` query parameters to the url, like this:

``http://your-host/services/<servce>_<service_version>/~monitor?end=<...>?start=<...>``

The `end` and `start` query parameters needs to have the following format: 
``YYYY-MM-DD[T]HH:MM[:SS[.ffffff]][Z or [±]HH[:]MM]]]``, so for instance: 2020-01-01 02:30

It it also possible to specify which variables to query time-series by specify the query parameter 
`variables`, like this:

``http://your-host/services/<servce_name>_<service_version>/~monitor?end=<...>?start=<...>?variables=v1?variables=v2``

This will query time-series data for variable `a` and `b`. The returned json time-series data will be on the following format:

.. code-block::

    {
        "a": {
            "timestamp": [t1, t2, ..., tn]
            "value": [v1, v2, ..., vn]
            }
        "b": {
            "timestamp": [t1, t2, ..., tn]
            "value": [v1, v2, ..., vn]
            }
    }

Example, using the `requests <https://requests.readthedocs.io/en/master/>`_
package in python::

    response = requests.GET(
        "services/name_version/~monitor",
        headers={"Authorization": f"Bearer {TOKEN}"})
    data = response.json()



**Option 2: CSV files**

The time-series data can also be returned in csv format, the entrypoint for this is:

``http://your-host/services/<servce_name>_<service_version>/~csv``

It is possible to specify, which variables and in during which time interval to query
time-series data for by using the following query parameters:
`end`, `start` and `varaibles`. For instance:


``http://your-host/services/<servce_name>_<service_version>/~monitor/csv?end=<...>?start=<...>?variables=v1?variables=v2``

The `end` and `start` query parameters needs to have the following format: 
``YYYY-MM-DD[T]HH:MM[:SS[.ffffff]][Z or [±]HH[:]MM]]]``, so for instance: 2020-01-01 02:30

This will query time-series data for variable `a` and `b`.This entrypoint returns a zip file containing one csv file per requested variable.
The csv files has the following format:

.. list-table::
   :widths: 25 25
   :header-rows: 1

   * - timestamp
     - value
   * - t1
     - v1
   * - t2
     - v2

**Option 3: The whole service database**

The time-series data is stored a in sqlite databases and the whole
service database can be requested at the following entrypoint:

``http://your-host/services/<servce_name>_<service_version>/~monitor/db``

Limiting the Number of Records in the Database
----------------------------------------------

Service databases are not intended to be permanent data storage. Records are kept for
90 days by default, but if a service stores large amounts of data often there is a
risk of filling the disk of the host machine. To prevent this it's possible to change
how many instances of each variable can be stored or to automatically remove old instances.
The database is cleaned at even intervals.

These options are set using a pair of environment variable in the service's runtime.
The easiest way to set these are in `.s2i/environment`:

    * DAEPLOY_SERVICE_DB_TABLE_LIMIT
        * Should have the format <number><limiter>
        * Limiter options: rows, days, hours, minutes or seconds.
    * DAEPLOY_SERVICE_DB_CLEAN_INTERVAL
        * Should have the format <number><limiter>
        * Limiter options: days, hours, minutes or seconds.

To limit the number of days to store variables to 30 we would add the following
to `.s2i/environment`::

    DAEPLOY_SERVICE_DB_TABLE_LIMIT=30days
