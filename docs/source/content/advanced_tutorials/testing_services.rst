.. _testing-services-reference:

Testing Services Before Deployment
==================================

Iteratively debugging a service by repeatedly deploying and calling entrypoints
can become a somewhat slow and tedious process, having to wait a short time
for every deploy. To help ensure that services are in
a working state before deployment, we recommend that you use an automated
testing framework. When creating a new project with ``daeploy init`` a `test/`
directory is created. It contains two files: `base_functionality_test.py`
that performes base tests for things that are necessary for these services
to work, and `user_tests.py` for the user to add their own tests.

Writing Tests
-------------

The tests use `pytest <https://docs.pytest.org/en/stable/>`_ which requires the
tests to lay in a folder called `tests/`, in modules that end with `_test.py`
and the names of the test functions should start with `test_`. Tests use the
``assert`` statement to see if code behaves as expected. Let's use the `hello`
service that is generated with ``daeploy init`` for an example test

.. testcode::

    import logging
    from daeploy import service
    from daeploy.communication import notify, Severity

    logger = logging.getLogger(__name__)

    service.add_parameter("greeting_phrase", "Hello")

    @service.entrypoint
    def hello(name: str) -> str:
        greeting_phrase = service.get_parameter("greeting_phrase")
        if name == "World":
            notify(
                msg="Someone is trying to greet the World, too time consuming. Skipping!",
                severity=Severity.WARNING,
                emails=None,
            )
            return "Greeting failed"
        logger.info(f"Greeting someone with the name: {name}")
        return f"{greeting_phrase} {name}"


    if __name__ == "__main__":
        service.run()


The output of the :py:func:`hello()` function can be tested with the following function

.. testcode::

    # <project_path>/tests/user_tests

    def test_hello():
        # Test that service.hello("Bob") returns what is expected
        assert service.hello("Bob") == "Hello Bob"

We can run the tests using:

>>> daeploy test <project_path> # doctest: +SKIP

Which is equivalent to:

>>> cd <project_path> # doctest: +SKIP
>>> python3 -m pytest . # doctest: +SKIP


Functions That Do Not Work Locally
----------------------------------

There are three ways to run an Daeploy service. We have seen how to deploy and run
your services to a manager using ``daeploy deploy`` many times now, but you could also
run it with ``python <project_path>/service.py`` in which case it will be run as
it's own webserver on localhost if `service.py` ends with
:py:func:`daeploy.service.run()`. If it does not have :py:func:`daeploy.service.run()`
it will behave like a normal python module and the functions therein can be used
however you'd like. The  ``if __name__ == "__main__"`` clause that surrounds 
:py:func:`daeploy.service.run()` allows us to import `service.py` freely and use it's
functions. However, the SDK will only have full functionality if run on a manager.
The table below shows the SDK functions that cannot run locally without a manager:

+-----------------------------------------------+----------+-----------+---------+
| Functions                                     | Module   | Localhost | Manager |
+-----------------------------------------------+----------+-----------+---------+
| :py:func:`daeploy.communication.call_service` | No       | No        | Yes     |
+-----------------------------------------------+----------+-----------+---------+
| :py:func:`daeploy.communication.notify`       | No       | No        | Yes     |
+-----------------------------------------------+----------+-----------+---------+
| :py:func:`daeploy.service.store`              | No       | Yes       | Yes     |
+-----------------------------------------------+----------+-----------+---------+
| :py:func:`daeploy.service.call_every`         | No*      | Yes       | Yes     |
+-----------------------------------------------+----------+-----------+---------+

\*Will not repeat without starting the service with :py:func:`daeploy.service.run()`
but it won't cause any errors


Mocking Functions to Run Services Locally
-----------------------------------------

To be able to test services that depend on some of the functions listed above, we
have to use something called mocking, which means to templorarily replace code to
do something else. In the case of the `hello` service we would get an error if
:py:func:`~daeploy.communication.notify` was called. We could mock
:py:func:`~daeploy.communication.notify` to do nothing and then check if it was called
to test that a notification would be posted to the manager. In :py:mod:`daeploy.testing`
there is a function :py:func:`~daeploy.testing.patch` that is included in Daeploy for
convenience from :py:mod:`unittest.mock` and is used for mocking

.. testcode::
    :skipif: True

    # <project_path>/tests/user_tests
    import service
    from daeploy.testing import patch


    def test_notify_called():
        # Test that notify() is called when running service.hello("World")
        with patch("service.notify") as notify:
            service.hello("World")
            notify.assert_called()

We import `service.py` and :py:func:`~daeploy.testing.patch` and then in the test function
we create a session scope for the patch to revert the change back once we are done. In
:py:func:`~daeploy.testing.patch` we give a path to the function to mock, in this case the
:py:func:`~daeploy.communication.notify` function that we imported in `service.py`. We can
then call the :py:func:`hello` function as normal and use the mock object
:py:obj:`notify` to check if :py:func:`~daeploy.communication.notify` was called in
:py:func:`service.hello`. The process for mocking :py:func:`~daeploy.service.store` is
very similar, because neither :py:func:`~daeploy.service.store` or
:py:func:`~daeploy.communication.notify` have any return values.

:py:func:`~daeploy.service.call_service` on the other hand, will often have return values
and testing a service that uses it requires you to mock a problem specific return value.
Let's take a look at an example service

.. testcode::

    import logging
    from daeploy import service
    from daeploy.communication import call_service

    logger = logging.getLogger(__name__)

    @service.entrypoint
    def ping_service(service_name: str) -> str:
        logger.info(f"Pinging: {service_name}")
        response = call_service(
            service_name=service_name,
            entrypoint_name="ping",
        )
        return response


    if __name__ == "__main__":
        service.run()

This service has an entrypoint that pings another service to see if it is responding.
To create an automated test for this we need to mock :py:func:`~daeploy.service.call_service`
to return something that we would expect the :py:func:`ping` entrypoint of the target
service to return in a real scenario

.. testcode::
    :skipif: True

    # <project_path>/tests/user_tests
    import service
    from daeploy.testing import patch


    def test_ping_service():
        with patch("service.call_service") as call_service:
            call_service.return_value = "Responding"
            service.ping_service("test_service")
            call_service.assert_called()

Here we mock :py:func:`~daeploy.service.call_service` in the same way as we did with
:py:func:`~daeploy.communication.notify` but we add a return value to the mock object
:py:obj:`call_service` to make it return that when it is called in
:py:func:`service.ping_service`.

.. note:: The :py:func:`patch` function returns an object of the
    `Mock <https://docs.python.org/3/library/unittest.mock.html#unittest.mock.Mock>`_
    class from :py:mod:`unittest.mock`.


More Testing
------------

Refer to the `pytest <https://docs.pytest.org/en/stable/>`_ documentation and its
many addons if you would like to do more testing. To learn more about mocking and
the :py:func:`patch` function, take a look at
`unittest.mock <https://docs.python.org/3/library/unittest.mock.html>`_.
