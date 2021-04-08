.. _cross-service-reference:

Cross-service Communication
===========================

Microservices is a modern software architectural style where an application consists
of a collection of loosely coupled and independently deployable services. These
small services communicate with each other to form large and complex applications.

In this tutorial we will build a yatzee game consisting of two services, one that
throws a die and another that handles the game logic.

Die Roller Service
-------------------

The first service we create will generate a random number between 1 and 6 and
respond with the result:

>>> daeploy init # doctest: +SKIP
project_name [my_project]: die_roller_service

Modify the code in `service.py` to

.. literalinclude:: ../../../../examples/cross_service_communication/die_roller_service/service.py

Deploy the service:

>>> daeploy deploy die_roller 1.0.0 ./die_roller_service # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME         VERSION    STATUS    RUNNING
------  -----------  ---------  --------  -----------------------------------
*       die_roller   1.0.0      running   Running (since 2020-11-24 11:56:18)

You can test if the service works correctly by going to the interactive 
documentation at http://your-host/services/die_roller/docs.

Yatzee Service
--------------

The `yatzee` service will call the :py:func:`roll_die` method of the `die_roller`
for each die in play. If the player gets a yatzee (all 6s) we send a notification!
Let's create the code for that service:

>>> daeploy init #doctest: +SKIP
project_name [my_project]: yatzee_service

And modify `service.py` to

.. literalinclude:: ../../../../examples/cross_service_communication/yatzee_service/service.py

Deploy the service:

>>> daeploy deploy yatzee 1.0.0 ./yatzee_service # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
*       yatzee  1.0.0      running   Running (since 2020-11-24 12:15:57)

We use the :py:func:`~daeploy.communication.call_service` function to call an entrypoint in
another service. In this case, the :py:func:`roll_die` function of the `die_roller`
service. Notice how we did not specify any version of `die_roller`, this way
the main version will be used. If you wanted to specify a version, then you should
use the keyword argument ``service_version``.

Try out your new service at http://your-host/services/yatzee/docs.

What's Next?
------------

Now that you've come this far you have seen most of the fundamentals of Daeploy. 
Be sure that you have taken a look at the documentation for the
:ref:`sdk-reference` and the :ref:`cli-reference`. After which you should be ready
to move on to the advanced tutorials.
