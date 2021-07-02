.. _notifications-reference:

Notifications
=============

Notifications is another feature of Daeploy. When a notification is raised it can be viewed
on the dashboard at http://your-host or sent to an email address. They have several use-cases,
such as catching unexpected behaviour of your program or as alarms to act upon.
To add a notification we use the :py:func:`~daeploy.communication.notify` function.
It can be placed in a conditional statement to send a notification if it's true. 

Let's say you want to add a notification to the ``daeploy init`` service when
someone tries to greet the world, because that would take a lot of time.
Then we add an if-statement to check the input and send the notification.
After the notification is sent we raise a :py:class:`~daeploy.exceptions.HTTPException`
with the status code `403 - Forbidden`, to show the user that their request
was rejected. With this added, the :py:func:`hello` will look like this:

.. literalinclude:: ../../../../examples/notifications_example/service.py

Email Notifications
-------------------

The notifications sent by the :py:func:`~daeploy.communication.notify` call above will only
show up on the dashboard, but it is also possible to send them as emails as well. For this,
the manager has to be configured with an email and an SMTP server. Please refer to the
documentation on the manager configuration: :ref:`email-config-reference`.

To send the emails we use the ``emails`` keyword argument of the :py:func:`~daeploy.communication.notify`
function that takes a list of emails as input. So to send an email notification we could write::

    notify(
            msg="Trying to greet world. Too time consuming!",
            severity=Severity.WARNING,
            emails=["your@email.com"],
        )

.. tip:: To make the email recipients dynamically changeable, you can add
    the emails as a parameter with :func:`~daeploy.service.add_parameter`.
