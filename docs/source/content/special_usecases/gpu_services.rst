.. _gpu-service-reference:

Access NVIDIA GPUs
==================

.. warning:: This is an experimental feature and has not been extensively tested.

Prerequisites
-------------

To enable this feature, make sure you have a cuda-enabled GPU with the correct
drivers installed on your manager host. Drivers are available from
`nvidia drivers page <https://www.nvidia.com/Download/index.aspx>`_. 

.. note:: Make sure you have no containers running on your machine before continuing.

Installing nvidia-container-runtime
-----------------------------------

Follow the steps 
`here <https://github.com/NVIDIA/nvidia-container-runtime#installation>`_ to install
the `nvidia-container-runtime`. The same URL describes a few ways to register the
runtime. For the nvidia containers to play nicely with Daeploy you should `edit the
daemon.json <https://github.com/NVIDIA/nvidia-container-runtime#daemon-configuration-file>`_ 
configuration file and set nvidia as the default runtime.

Restart docker:

>>> sudo systemctl daemon-reload  # doctest: +SKIP
>>> sudo systemctl restart docker  # doctest: +SKIP
At this point you can start a manager on this machine and use it like normal.

Deploying services with GPU access
----------------------------------

Services will not automatically use the GPU even with nvidia-container-runtime enabled,
for the GPU to be available you must first set an environment variable in
`.s2i/environment`. Add the row:

.. code-block:: none

    NVIDIA_VISIBLE_DEVICES = all

to expose all GPUs to a service. Take a look the
`nvidia environment variables <https://github.com/NVIDIA/nvidia-container-runtime#environment-variables-oci-spec>`_
to see the available options. Now if you deploy the service with ``daeploy deploy``
it will run in a container with access to cuda resources.