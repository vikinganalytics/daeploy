
.. _Manager-configuration-reference:

Manager Configuration
=====================

The Manager is highly configurable using environment variables.

+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| Environment Variable                       | Default Value         | Description                                                 |
+============================================+=======================+=============================================================+
| DAEPLOY_HOST_NAME                          | "localhost"           | Host name of the machine running the Manager.               |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_PROXY_HTTP_PORT                    | 80                    | Proxy port for HTTP communication with Manager.             |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_PROXY_HTTPS_PORT                   | 443                   | Proxy port for HTTP communication with Manager.             |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_PROXY_CONFIG_PATH                  | "proxy_config"        | Path to proxy configuration files.                          |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_AUTH_ENABLED                       | False                 | Using the Manager requires login if true.                   |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_LOG_LEVEL                          | "INFO"                | Minimum logger level for Manager.                           |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_ACCESS_LOGS_ENABLED                | True                  | Whether to print access logs.                               |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_PROXY_HTTPS                        | False                 | Sets up a secure connection to the Manager if true          |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_HTTPS_STAGING_SERVER               | False                 | Sets if a staging server without rate limits should be used |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_CONFIG_EMAIL                       | null                  | Email address HTTPS and sending notifications.              |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_CONFIG_EMAIL_PASSWORD              | null                  | Password for config email, only required for notifications. |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_NOTIFICATION_SMTP_SERVER           | null                  | SMTP server URL.                                            |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_NOTIFICATION_SMTP_PORT             | null                  | Port to SMTP server, usually 587 or 465.                    |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_ACTIVATION_KEY                     | ""                    | License activation key. Without key Manager lives for 12h.  |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+
| DAEPLOY_ADMIN_PASSWORD                     | admin                 | Password for the admin user. Defualt to admin.              |
+--------------------------------------------+-----------------------+-------------------------------------------------------------+

User Management
---------------

The manager always has an admin user with a password that is set with the `DAEPLOY_ADMIN_PASSWORD` environment variable.
To configure other users, it is easiest to use the CLI ``daeploy user`` commands. This way you can add, list, remove and
change passwords for non-admin users.

.. note:: The only difference between the admin and other users so far, is that the admin can create new users. A more
    sophisticated privileges system is planned for a future release.

Secure Manager Connection
-------------------------

It is possible to get a secure HTTPS connection to the Manager using automatically
created certificates from `Let's Encrypt <https://letsencrypt.org>`_. To enable HTTPS you must
start a new Manager with the environment variable
``DAEPLOY_PROXY_HTTPS`` set to true. We also recommend that you set an email
address with the environment variable ``DAEPLOY_CONFIG_EMAIL``, so you can get
notified if the certificate is about to run out. 

.. warning:: For the `Let's Encrypt` certificates to work,
    the server must have a valid hostname which resolves via DNS to the server's IP
    address. It will not work if you access the Manager using an IP address or
    ``localhost`` due to how TLS certificates are generated.


.. _email-config-reference:

Email notifications
-------------------

The first step is to set up an email address that the Daeploy Manager can use to send
the notification emails. For this you need an
`SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`_ server with
an email account that you can use. We recommend to have a dedicated email address
for sending notifications.

The Manager is configured with a notification sender email at startup. We do this
by setting four different environment variables at Manager startup

+--------------------------------------------+-----------------------+
| Environment Variable                       | Value                 |
+============================================+=======================+
| DAEPLOY_CONFIG_EMAIL                       | "email@address.com"   |
+--------------------------------------------+-----------------------+
| DAEPLOY_CONFIG_EMAIL_PASSWORD              | "password"            |
+--------------------------------------------+-----------------------+
| DAEPLOY_NOTIFICATION_SMTP_SERVER           | "smtp.server.url"     |
+--------------------------------------------+-----------------------+
| DAEPLOY_NOTIFICATION_SMTP_PORT             | Usually 587 or 465    |
+--------------------------------------------+-----------------------+

Upon startup of the Manager, if everything worked, an email will be sent from
"email@address.com" to itself, to show that it successfully connected. Otherwise,
as long as the Manager could still start, any issues with the email configuration 
will be viewable on the notification tab in the dashboard.

Log configuration
-----------------

All logging in Daeploy is done directly to stdout and stderr and relies heavily on the
built-in logging features of the docker daemon. As such, any configuration of log
rotation etc needs to be done on the docker daemon level.

Daeploy takes care of setting reasonable log configuration options on all the
*services* that are started. For each service, this means that log files are rotated when
they grow above 100MB in size and a maximum of 3 such files are kept on disk.

For the Manager container however, the log configuration is left to the user. But we give
some hints here on reasonable options. In general, the docker daemon and its logging
mechanism can be configured in two ways, either by editing the ``daemon.json`` configuration
file (which sets daemon-wide default configurations) or by providing container-specific
configuration when starting a new container with ``docker run``. For more details, please
have a look at the `docker docs <https://docs.docker.com/config/containers/logging/configure/>`_.

An example container-specific configuration could be provided as such (maximum of 5 log
files no larger than 10 megabytes each using the JSON log handler (the docker daemon default))::

    docker run ... --log-driver json-file --log-opt max-size=100m --log-opt max-file=5

.. warning:: By default, the docker daemon is configured to *NOT* do any log rotation at all,
    meaning that it will slowly fill up the HDD of the host. To avoid any problems
    originating from a full HDD, we highly recommend setting a specific log configuration
    for the Manager container when starting.

Changing Ports
--------------

If you want to change the port that the manager is running on, you have to set the
environment variable ``DAEPLOY_PROXY_HTTP_PORT`` or ``DAEPLOY_PROXY_HTTPS_PORT`` as
well as changing the published port of the container with
``docker run -p external:internal ...``. The manager application assumes that the
external and internal ports are the same.

Typical production setup
------------------------

Below we show an example of a typical production setup using the Docker CLI
and the
`start_manager script <https://github.com/vikinganalytics/daeploy-examples/blob/master/start_manager>`_.
In the example we start a Manager instance listening on ``my.domain.com``, with HTTPS,
authentication, an activated license and email notifications enabled.

Docker CLI
^^^^^^^^^^

.. code-block:: shell

    # We create a docker volume for keeping our data persistent across restarts/upgrades
    docker volume create daeploy_data  

    docker run \
        --name daeploy_manager \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -v daeploy_data:/data \
        -p 80:80 \
        -p 443:443 \
        -e DAEPLOY_HOST_NAME=my.domain.com \
        -e DAEPLOY_PROXY_HTTPS=True \
        -e DAEPLOY_AUTH_ENABLED=True \
        -e DAEPLOY_ACTIVATION_KEY=... \
        -e DAEPLOY_ADMIN_PASSWORD=... \
        -e DAEPLOY_CONFIG_EMAIL=<some@email.com> \
        -e DAEPLOY_CONFIG_EMAIL_PASSWORD=<password for some@email.com> \
        -e DAEPLOY_NOTIFICATION_SMTP_SERVER=<your smtp server address> \
        -e DAEPLOY_NOTIFICATION_SMTP_PORT=<your smtp server port> \
        --restart always \
        --log-driver json-file \
        --log-opt max-size=100m \
        --log-opt max-file=5 \
        -d daeploy/manager:{version} \

.. tip:: To ease working with all environment variables, it is possible to make use
    of the ``--env-file`` parameter to ``docker run``. 
    See `here <https://docs.docker.com/engine/reference/commandline/run/#set-environment-variables--e---env---env-file>`_
    for details on syntax etc.

start_manager script
^^^^^^^^^^^^^^^^^^^^

To reduce the complexity of launching the manager we have created a simple script
``start_manager`` that hides much of the complexity while still leaving all
manager settings available.

    bash start_manager \
        --version ... \
        --host-name my.domain.com \
        --auth-enabled \
        --https-enabled \
        --activation-key ... \
        --admin-password ... \
        --config-email ... \
        --config-password ... \
        --smtp-server ... \
        --smtp-port ... \

.. tip:: You can use ``start_manager --help`` to get a short description of the
    available options.
