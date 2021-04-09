.. _cli-deploy-reference:

Deployment Options
==================

There are a few ways to use the ``deploy`` command from the :ref:`cli-reference`
that we haven't looked at until this point. In this tutorial we will look at
those, to make sure you have a good idea of the options you have available.

.. Note:: Always remember the ``--help`` option. It can be used with each command as well
    as the whole ``daeploy`` command-line app to get a description of what options you
    have. If you are unsure how and what-for a certain command is used, it should
    be your go-to option.

Daeploy supports three separate service sources; A local source (directory or tarball),
a git repository or a container image. By default ``deploy`` will expect a local
source and to deploy from another source you need to add a flag with your ``deploy``
command:

+-------------+--------------+
| Long Option | Short option |
+=============+==============+
| --git       | -g           |
+-------------+--------------+
| --image     | -i           |
+-------------+--------------+

.. note:: Daeploy uses `Source-To-Image <https://github.com/openshift/source-to-image>`_
    to automatically convert source code into container images. There are advanced
    options that can be specified in `s2i/` and `.s2iignore` to tailor the containerization
    to your service.

Git Repository
--------------

The ``--git`` option is used to deploy an onlie git repository. It is functionally
identical to deploying from a local directory and have the same requirements on the
contents of the service. To deploy a service from a public git repository:

>>> daeploy deploy my_service 1.0.0 --git https://github.com/sclorg/django-ex # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME        VERSION    STATUS    RUNNING
------  ----------  ---------  --------  -----------------------------------
*       my_service  1.0.0      running   Running (since 2020-11-23 16:56:06)

For a private git repository, access credentials of some sort is needed. For Github, this
comes down to creating a Personal Access Token
(`PAT <https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token>`_)
and using it like so:

>>> daeploy deploy my_service 1.0.0 --git https://USERNAME:TOKEN@github.com/me/private_repository # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME        VERSION    STATUS    RUNNING
------  ----------  ---------  --------  -----------------------------------
*       my_service  1.0.0      running   Running (since 2020-11-23 16:56:06)

Container Image
---------------

The ``--image`` option can be used to deploy any container image as a Daeploy service.
This can be useful for deploying applications that are not written using the
SDK within the Daeploy framework. Keep in mind that most pre-build images will not
support the automatic interactive documentation:

>>> daeploy deploy --image my_service2 1.0.0 traefik/whoami --port 80 # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME         VERSION    STATUS    RUNNING
------  -----------  ---------  --------  -----------------------------------
*       my_service2  1.0.0      running   Running (since 2020-11-23 16:57:55)

In the last command we used an optional argument to change the internal port of
the service container. This is not required when deploying services locally or
from git repositories, but it might be necessary when deploying from an image.

Advanced Deployment of Docker Images
------------------------------------

Extra ``key: value`` arguments (beyond port number and environment variables) needed for the docker image
to run properly can be specified when deploying the image via the ``/~image`` POST HTTP endpoint. These extra
``key: value`` arguments should be specified under the ``docker_run_args`` key in the request data field. The accepted
parameters for ``docker run`` which can be found `here <https://docker-py.readthedocs.io/en/stable/containers.html>`_.

For instance, a docker image
that requires ``privileged`` mode to run properly can be deployed like (using pythons request library)::

    requests.post(
        url='http://your-host/~image,
        headers=<headers>,
        data = {
            'image': <image>,
            'name': <name>,
            'version': <version>,
            'port': <port>,
            'docker_run_args': {
                'privileged': True,
                ...
            }
        })

Ignoring Files when Deploying
-----------------------------

Sometimes not all the contents of a service have to be included when the service
is deployed. Common exceptions can include test folders and configuration files.
To exclude a file or a folder from being deployed you can specify their path
in `.s2iignore`. By default, the `.git/` and `test/` directories are excluded
because they do not contribute to the functionality of a service.
