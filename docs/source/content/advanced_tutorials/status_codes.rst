.. _http-status-reference:

HTTP Status Codes
=================

In Daeploy, when an API entrypoint function gets to a ``return`` statement, the
default behaviour is to respond with a status code of 200. If an exception
is raised somewhere in the function, it will return a `500 Internal Server Error`-response,
which just means that there has been an internal error. Generally you never
want to show any 500-responses to the users of the API. Let's look at an example
that responds with other status codes to see how it can be done:

.. literalinclude:: ../../../../examples/status_code_example/service.py

For :py:func:`create_new_dict` in this example, we have changed the status code
of a successful request to be `201 Created` instead of `200 OK`. If we try to
create a new dictionary when it already exists we raise an :py:class:`HTTPException`,
which makes the entrypoint respond with that status code and the detail in
the response body.

.. Note:: Here is a full list of `HTTP status codes <https://en.wikipedia.org/wiki/List_of_HTTP_status_codes>`_ 
