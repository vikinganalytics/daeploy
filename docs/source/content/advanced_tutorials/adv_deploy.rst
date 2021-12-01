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

Daeploy supports several service sources; A local source (directory or tarball),
a git repository or docker images. By default ``deploy`` will expect a local
source and to deploy from another source you need to add a flag with your ``deploy``
command:

+---------------+--------------+
| Long Option   | Short option |
+===============+==============+
| --git         | -g           |
+---------------+--------------+
| --image       | -i           |
+---------------+--------------+
| --image-local | -I           |
+---------------+--------------+

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
The manager will look for the image first in it's local system, then on docker hub.
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

Local Container Image
---------------------

To avoid having to manually upload images from your development setup to the manager
you can use the ``--image-local`` flag. For this you need to have docker installed on
your development machine. The given image will be saved as a tar file and uploaded to
the manager and deployed from there. Assuming you have a project with a dockerfile,
you could deploy that project as a service on daeploy with the following commands:

>>> docker build -t image_name:tag path/to/project # doctest: +SKIP
>>> daeploy deploy --image-local my_service 1.0.0 image_name:tag # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME         VERSION    STATUS    RUNNING
------  -----------  ---------  --------  -----------------------------------
*       my_service   1.0.0      running   Running (since 2021-09-06 15:53:55)

Environment Variables
---------------------

.. _cli-deploy-envvar-reference:

It is possible to set environment variables at deployment time using the CLI
``--environment/-e`` option. The variables are given to the CLI in the format
``VARIABLE=VALUE`` or simply ``VARIABLE`` to copy that variable from your
development environment (if it exists). Multi-word variable values should be
enclosed by quotation marks.

.. note:: Setting environment variables at run time will overwrite any variables
    defined in the `.s2i/environment` file.

>>> daeploy deploy example_service 1.0.0 -e VAR=VAL -e LONGVAR="variable with spaces" ./service_path # doctest: +SKIP

Container Run Arguments
-----------------------

Extra ``key: value`` arguments (beyond port number and environment variables) needed for the docker image
to run properly can be specified when deploying the image via the ``/~image`` POST HTTP endpoint. These extra
``key: value`` arguments should be specified under the ``run_args`` key in the request data field. The accepted
parameters for ``docker run`` can be found `here <https://docker-py.readthedocs.io/en/stable/containers.html>`_.

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
            'run_args': {
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


Source to Image and Builder Images
----------------------------------

Daeploy uses something called `Source to Image (S2I)
<https://github.com/openshift/source-to-image>`_ behind the hood to convert
source code to container images. S2I injects that source code into an existing
image, called a builder image, which it uses to produce a ready-to-run image.

There exists a number of ready-made builder images for python and we have
developed our own lightweight python builder images specifically for use with
Daeploy (`github link
<https://github.com/vikinganalytics/daeploy-s2i-python>`_). `Click here
<https://hub.docker.com/r/daeploy/s2i-python/tags>`_ for a full list of
available tags. 

By default Daeploy uses a builder image based on ubuntu with python 3.8. There
can be situations, however, where that image might not be suitable. For
example if you want to use some library that is not supported for that version
of python, or if you need a certain OS.

To change the builder image you can use the ``--build-image`` option from the
deployment command in the CLI. We recommend using one of the custom made builder
images for Daeploy, but any python S2I builder images will work.

Injecting Additional Assembly Steps
-----------------------------------

If your application is dependent on software that must be installed on the OS level,
it is not necessary to change the entire build image, but to instead add an additional
step to the existing build process.

The build process of S2I contains of three things:

1. A dockerfile
2. An assemble script
3. A run script

The dockerfile is used to set up the OS and inject the source code into the
service. The `assemble` script is run after the dockerfile to set up the runtime
environment, e.g. installing required software and dependencies. The `run` script
starts the application after assembly. It will try to run the file defined by the
``APP_SCRIPT`` or ``APP_FILE`` environment variables.

Both the assemble and run scripts can be hooked into to add additional steps when
building or starting the service. To do this we add `.s2i/bin/assemble` or
`.s2i/bin/run` scripts in the service code.

An example of an `assemble` script could look like this::

    #!/bin/bash
    # Running stock assemble script
    ${STI_SCRIPTS_PATH}/assemble
    # Add additional assembly steps here

And a `run` script::

    #!/bin/bash
    # Add additional run steps here

    # Running stock run script
    ${STI_SCRIPTS_PATH}/run
