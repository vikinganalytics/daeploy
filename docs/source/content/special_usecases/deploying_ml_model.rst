.. _deploy-ml-reference:

Deploying Machine Learning Models
=================================

Machine Learning models are commonly trained in a separate environment from
the deployment environment. The models are typically serialized as e.g.
`pickle <https://docs.python.org/3/library/pickle.html>`_ files, which can easily
be moved between the environments. In this tutorial we are going to look at how we
can take a pickled `sklearn <https://scikit-learn.org/stable/>`_ classifier model
and create a service that uses that model to predict a class on data sent to it.

The Classifier
--------------

Let's create a simple classifier for the famous iris dataset in this example.
We will not go into any detail about how it's done. There are plenty of tutorials
online that go through this process:

.. literalinclude:: ../../../../examples/ml_model_serving/train_model.py

The Service
-----------

Like we have done previously we use ``daeploy init`` command to create a new project.

>>> daeploy init # doctest: +SKIP
project_name [my_project]: iris_project

The first thing we have to do is to create a directory in `iris_project` to put our
model.

>>> mkdir iris_project/models # doctest: +SKIP
>>> mv classifier.pkl iris_project/models/ # doctest: +SKIP

While it's fresh in our memory, let's add ``sklearn`` to the `requirements.txt` file,
because while a pickled object does not require its dependencies to be imported, they
still have to be installed. `requirements.txt` should contain the following:

.. literalinclude:: ../../../../examples/ml_model_serving/iris_project/requirements.txt

A very simple service to make predictions using the
classifier we just trained could look like this:

.. literalinclude:: ../../../../examples/ml_model_serving/iris_project/service.py

In this service we unpickle the model as a global variable so we can use it anywhere
in the service and we create the prediction entrypoint:

.. literalinclude:: ../../../../examples/ml_model_serving/iris_project/service.py
    :pyobject: predict

The entrypoint simply calls the predict method of the classifier, writes some logs
and responds with the result. Thanks to the special input and output types that
we describe in :ref:`sdk-typing-non-json-reference`, we don't have to worry
about converting the input and output to json compatible types.

Deployment
----------

Just like before, we deploy the service using the CLI:

>>> daeploy deploy iris_classifier 1.0.0 ./iris_project # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME             VERSION    STATUS    RUNNING
------  ---------------  ---------  --------  -----------------------------------
*       iris_classifier  1.0.0      running   Running (since 2020-11-23 16:22:46)

The service should now be up and running. Go to the documentation to test it out:
http://your-host/services/iris_classifier/docs. The data should be on a format
that can be transformed to a pandas dataframe, for example::

    {
        "data":
        {
            "col1": [1, 2],
            "col2": [1, 2],
            "col3": [1, 2],
            "col4": [1, 2],
        } 
    }

.. Note:: To get validation on your entrypoint input you should take a look at
    :ref:`sdk-typing-reference`.
