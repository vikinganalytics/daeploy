.. _versioning-shadow-reference:

Versioning and Shadow Deployment
================================

Daeploy supports something called shadow deployment, which means to deploy new versions
of a program "in the background" of an older version that is known to be stable.
This way, two or more services can run side by side and it becomes easy 
to test new versions in an undisruptive manner, without risking crashes or
other unwanted behaviour in production.

This works by mirroring the input to every version of a service, but only
returning the response of the main verision.

Deploying a Shadow Service
--------------------------

Deploying a shadow service in Daeploy is as easy as deploying any other service.
When deploying a service for the first time, it will always be the main version
and every subsequent service with the same name will be a shadow of the main
service. Let's try this out with the `hello` service we get from ``daeploy init``:

(If you still have a `hello` service running from a previous tutorial,
you can skip to the third step)

>>> daeploy init # doctest: +SKIP
project_name [my_project]: hello

>>> daeploy deploy hello 1.0.0 ./hello # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
*       hello   1.0.0      running   Running (since 2020-11-23 11:30:00)

>>> daeploy deploy hello 2.0.0 ./hello # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
        hello   2.0.0      running   Running (since 2020-11-23 11:31:44)

>>> daeploy ls # doctest: +SKIP
Active host: http://your-host
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
*       hello   1.0.0      running   Running (since 2020-11-23 11:30:00)
        hello   2.0.0      running   Running (since 2020-11-23 11:31:44)

The asterisk in the main column indicates that a service is the main version of
that service, otherwise it is a shadow. Each individual service can be reached at
http://your-host/services/name_version/ and the shadow deployment setup is
reached at http://your-host/services/name/. At this URL, requests will be sent
to every running service with that name, but you will only get the response from
the main. Functionally, it is identical to communicating with the main directly.
This way it's possible to use shadow deployment and still be able to communicate
with individual services.

Changing Main Service
---------------------

When a new service seems to perform to a satisfactory level you can change it to
the main service using the CLI command ``daeploy assign``:

>>> daeploy assign hello 2.0.0 # doctest: +SKIP
Active host: http://your-host
Change hello 2.0.0 to main? [y/N]: y
Changed main version to hello 2.0.0
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  -----------------------------------
        hello   1.0.0      running   Running (since 2020-11-23 11:30:00)
*       hello   2.0.0      running   Running (since 2020-11-23 11:31:44)

Now `hello 2.0.0` is the new main service and `hello 1.0.0` can be safely removed,
or kept running in the background and changed back to if there should be any
problems with the new version.

Killing Services
-----------------

The user is prohibited from killing main services while it has shadows. This
is to protect the user from accidentally removing the main service and disrupting
the production system. Shadow services can be killed freely or all versions of a
service can be killed simultaneously with ``daeploy kill <name>``. Main services
can be killed if they are the only service with that name.
