.. _conda-reference:

Using Daeploy with Conda
========================

If you prefer using conda over pip + venv you can still install Daeploy with pip
inside of your conda environment. Everything will work as usual in your
development environment:

>>> conda create --name myenv  # doctest: +SKIP
>>> conda activate myenv  # doctest: +SKIP
>>> conda install pip  # doctest: +SKIP
>>> pip install daeploy  # doctest: +SKIP

To check the installation, run:

>>> daeploy --help  # doctest: +SKIP

Conda in Production Environment
-------------------------------

``daeploy deploy`` from source code only uses pip, if you want to
run your service in a conda environment on the manager you have to build an
image from the service source code, forfeiting some of the convenience of Daeploy.
A minimal example:

>>> daeploy init  # doctest: +SKIP
project_name [my_project]: conda_daeploy_project

Add an `environment.yml` file to the repo by running:

>>> conda env export > conda_daeploy_project/environment.yml  # doctest: +SKIP

Add a `Dockerfile` to the project. A minimal working dockerfile can be::

    # Dockerfile
    FROM continuumio/miniconda3

    WORKDIR /app

    # Create the environment:
    COPY environment.yml .
    RUN conda env create -f environment.yml

    # Make RUN commands use the new environment:
    SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

    # The code to run when container is started:
    COPY service.py .
    ENTRYPOINT ["conda", "run", "-n", "myenv", "python", "service.py"]

.. Note::
    You will have to change `myenv` to the name of the environment described by
    `environment.yml` if you named it something else.

Create an image with:

>>> docker build -t conda_project ./conda_daeploy_project  # doctest: +SKIP

And save it as a tar file with:

>>> docker save conda_project -o ./conda_project.tar  # doctest: +SKIP

To run it on a remote manager you first have to upload the image. This is easiest
done from the manager API using the interactive documentation at http://your-host/docs.
Upload the image with ``/services/~upload-image`` and then you can deploy it with:

>>> daeploy deploy conda_project 1.0.0 -i conda_project  # doctest: +SKIP
