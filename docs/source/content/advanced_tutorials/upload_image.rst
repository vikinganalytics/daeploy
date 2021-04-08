
Upload local docker image
=========================

One can deploy pre-built docker images as services. If these pre-built docker images are 
publicly available at DOCKER HUB, one can use the ``/~image`` entrypoint via the manager docs or the ``--image`` flag when using the CLI,  
deploy the image as a service::
    
    >>> daeploy deploy --image my_service 0.1.0 my_image # doctest: +SKIP

If the pre-built docker images are only available locally on your machine, you have to upload the images to the manager host before they are deployed like above. 
To upload the images to the Daeploy manager host one can use the ``services/~upload-image`` entrypoint via the docs. This entrypoint takes as input a tar file, and to store 
your docker image as a tar file you can run::

    >>> docker save --output my_image.tar my_image # doctest: +SKIP

When the tar file containing the docker image is uploaded, you can deploy the image as a service like above. 

.. note:: When Daeploy services are killed, the running docker image is removed from the system. Therefore, the image needs to be uploaded again if you want 
    to deploy the image a second time.
