.. _dashboard-reference:

Dashboard
=========

The Daeploy Manager creates a dashboard that shows information about the services in a
graphical interface. The dashboard can be reached at the host url: http://your-host
after logging in. It consists of two tabs: services and notifications.

Services
--------

Here you can see all the running services on this host. It shows similar information
to the ``daeploy ls`` CLI command, such as service name, version, state, etc. There are
also links to the service logs and API documentation, which can be very convenient
when debugging a new service. The same logs can be reached using ``daeploy logs`` in the
CLI.

Notifications
-------------

This view shows any user-defined notifications that have been raised. It shows you
which service raised that notification, the message and the severity. Notifications
stack, meaning it does not print a new row every time a notification is raised, but
instead shows the count of each unique notification, so that the view does not
get cluttered with 100s of notifications.
