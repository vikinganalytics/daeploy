.. _reaching_service_from_external_applications:

Reaching a service from external applications
=============================================

If your service is running on a manager with authentication enabled, which it
should for a production setup, then any requests to that service must be
authenticated by including a valid authentication token. Tokens are
generated by the Daeploy Manager.

Generate an Authentication Token
--------------------------------

To generate an authentication token, you can use the CLI.
Make sure that you are logged in by calling the login command:

>>> daeploy login # doctest: +SKIP
Enter Daeploy host: http://your-host
Username: <username>
Password: <password>

When you are logged in, use the ``token`` command:

>>> daeploy token # doctest: +SKIP
Active host: http://your-host
Use the token in the request header {"Authorization": "Bearer token"}, for further details see the docs
{token}

This will generate a long-lived authentication token. This means that this token
remain valid indefinitely, which can potentially pose a security risk.

If you want a semi-long lived authentication token, specify the number of days it should
be valid by specifying an integer with your command call:

>>> daeploy token 10 # doctest: +SKIP
Active host: http://your-host
Use the token in the request header {"Authorization": "Bearer token"}, for further details see the docs
{token}

This will generate a token that is valid for 10 days.

Using the Authentication Token
--------------------------------------
Once you have generated the authentication token for your external application you are ready
to start sending requests to the deployed services.

The authentication token is used as a Bearer token and should be included in the header of the
applications requests to the services as key-value pair, like this:

``{"Authorization": "Bearer token"}``

For example, using the `requests <https://requests.readthedocs.io/en/master/>`_
package in python::

    TOKEN = "your_token"

    response = requests.post(
        "services/name_version/entrypoint",
        json={"data": "my_data"},
        headers={"Authorization": f"Bearer {TOKEN}"})
