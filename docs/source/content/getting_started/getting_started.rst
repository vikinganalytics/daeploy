.. _getting-started-reference:

Getting Started
===============

Daeploy consists of two components, a software development kit (SDK) and a manager application
that runs on the target machine. The SDK is a python library that you use in your
code to make into a service and the manager helps you deploy your code into running
applications.

Prerequisites
-------------

To use Daeploy, you need to have **python >= 3.6** installed in your development environment
and **docker** in your deployment environment.

Installation
------------

The Daeploy python library can be installed with `pip <https://pypi.org/project/daeploy/>`_:

>>> pip install daeploy  # doctest: +SKIP

Check your installation by running: ``daeploy --help`` in a terminal.

You will also need a manager container. To start a
manager running on ``localhost`` for development, run the following command:

>>> docker run -v /var/run/docker.sock:/var/run/docker.sock -p 80:80 -p 443:443 -d daeploy/manager:latest  # doctest: +SKIP

You can check that it started correctly by opening http://localhost/ in your browser.

.. warning:: This configuration should **never** be used in production. It is missing crucial
    features such as authentication and secured communication. Please refer to
    :ref:`manager-configuration-reference` for an example of a production setup.


Deploying Your First Service
----------------------------

Once the Manager is up and running you are ready to start using Daeploy. The
fastest and easiest way to interact with the Manager is to use the
:ref:`cli-reference` (CLI) that comes packaged with the SDK. The CLI contains a
host of useful commands that make the deployment and monitoring of services fast
and painless.

.. note:: You can call ``daeploy --help`` at any time, to get a list and short description of
    the available commands and ``daeploy <COMMAND> --help`` to get a longer description
    of that command.

Logging in to the Manager
-------------------------

The first step is to login to the host where Daeploy is running, if you started the manager with the
command above, your host is http://localhost. To do this, we call the ``daeploy login`` command.
If the manager has authentication enabled, you will be prompted for a username and password.

>>> daeploy login  # doctest: +SKIP
Enter Daeploy host: http://localhost

Once you have logged in you are connected to your specified host and able to
communicate with the Manager running there. Logins last for a week, before you
have to login again. We can check if we are logged in by calling:

>>> daeploy ls # doctest: +SKIP
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  ---------

It should return an empty list. If you didn't log in, you would get this message:

>>> daeploy ls # doctest: +SKIP
You must log in to a Daeploy host with `daeploy login` before using this command.
Aborted!

Creating a New Service
----------------------

When creating a new service we recommend the user to create a project template with:

>>> daeploy init # doctest: +SKIP
project_name [my_project]: my_first_daeploy_project

This creates a new directory called `my_first_daeploy_project` in
your current working directory. Let's see what's in it:

>>> ls -a ./my_first_daeploy_project  # doctest: +SKIP
.  ..  .s2i/  .s2iignore  README.md  requirements.txt  service.py  tests/

Let's not worry about the individual files and directories. For now it is enough
to know that `my_first_daeploy_project` contains a fully functioning hello world service
that we can deploy straight away.

Deploying the Service
---------------------

The CLI has a command to deploy a service. It requires that you to give it a name and
version and then specify the path to the project directory.

>>> daeploy deploy my_first_service 0.0.1 ./my_first_daeploy_project  # doctest: +SKIP
Deploying service...
Service deployed successfully
MAIN    NAME              VERSION    STATUS    RUNNING
------  ----------------  ---------  --------  -----------------------------------
*       my_first_service  0.0.1      running   Running (since 2020-11-20 15:48:45)

After a few seconds the service should be up and running. We can check with
``daeploy ls`` that it started properly.

>>> daeploy ls # doctest: +SKIP
MAIN    NAME              VERSION    STATUS    RUNNING
------  ----------------  ---------  --------  -----------------------------------
*       my_first_service  0.0.1      running   Running (since 2020-11-20 15:48:45)

If you open http://localhost in a browser you should see the dashboard where you
can get much of the same information as through the CLI. And at
http://localhost/services/my_first_service_0.0.1/docs you can read the automated
API documentation of the service and test its functionality.

.. note:: To communicate with your services from outside of the documentation you can use
    any HTTP library, which are available in most programming languages. In python
    `requests <https://requests.readthedocs.io/en/master/>`_ is commonly used or 
    `curl <https://curl.se/>`_ in bash.

Killing a Service
-----------------

Say that you are finished with your service, then the process can be stopped and the
service removed by calling:

>>> daeploy kill my_first_service 0.0.1  # doctest: +SKIP
MAIN    NAME              VERSION    STATUS    RUNNING
------  ----------------  ---------  --------  -----------------------------------
*       my_first_service  0.0.1      running   Running (since 2020-11-20 15:48:45)
Are you sure you want to kill the above service(s)? [y/N]: y
Service my_first_service 0.0.1 killed.

What's next?
------------

Now that you know the basics of how to deploy a service using the CLI it might be
time to learn how to write your own service: :ref:`custom-service-reference`,
or maybe take a look at the :ref:`cli-reference` documentaion.
