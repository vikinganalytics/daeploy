Source to Image and Builder Images
==================================

Daeploy uses something called `Source to Image (S2I)
<https://github.com/openshift/source-to-image>`_ behind the hood to convert
source code to container images. S2I injects that source code into an existing
image, called a builder image, which it uses to produce a ready-to-run image.

There exists a number of ready-made builder images for python and we have
developed our own lightweight python builder images specifically for use with
Daeploy (`github link
<https://github.com/vikinganalytics/daeploy-s2i-python>`_).

Changing Builder Images
-----------------------

By default Daeploy uses a builder image based on ubuntu with python 3.8. There
can be situations, however, where that image might not be suitable. For
example if you want to use some library that is not supported for that version
of python, or if you need a certain OS.

To change the builder image you can use the ``--build-image`` option from the
deployment command in the CLI. We recommend using one of the custom made builder
images for Daeploy, but any python S2I builder images will work.


Injecting Additional Assembly Steps
-----------------------------------

If your application is dependent on software that need to be installed on the OS level,
it is not necessary to change the entire build image, but to instead add an additional step
to the existing build process.

The build process of S2I contains of three things:

1. A dockerfile
2. An assemble script
3. A run script

The dockerfile is used to set up the OS and inject the source code into the
service. The `assemble` script is run after the dockerfile to set up the runtime
environment, e.g. installing required software and dependencies. The `run` script
starts the application after assembly. It will try to the file defined by the
``APP_SCRIPT`` or ``APP_FILE`` environment variables.

Both the assemble and run scripts can be hooked into to add additional steps when
building or starting the service. To do this we add `.s2i/bin/assemble` or
`.s2i/bin/run` scripts in the service code.

An example of an `assemble` script could look like this:

    #!/bin/bash
    # Running stock assemble script
    ${STI_SCRIPTS_PATH}/assemble
    # Add additional assembly steps here

And a `run` script::

    #!/bin/bash
    # Add additional run steps here

    # Running stock run script
    ${STI_SCRIPTS_PATH}/run
