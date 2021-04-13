.. _multiple-hosts-reference:

Using Multiple Hosts
====================

So far you have probably seen how to log in to a host with the ``daeploy login`` command,
but often you will be working on more than one machine, each running a manager.
Changing between managers is done with the ``daeploy login`` command just
like for the first manager and if you run the command now, you
should see someting like this:

>>> daeploy login # doctest: +SKIP
Current hosts:
0 - http://your-host
Enter Daeploy host: 

Type in the URL to the new host and your username + password and you will be 
logged in to the new host:

>>> daeploy login # doctest: +SKIP
Current hosts:
0 - http://your-host
Enter Daeploy host: http://your-new-host
Logging in to Daeploy instance at http://your-new-host
Username: <username>
Password: <password>
Changed host to http://your-new-host

Now if you call ``daeploy ls`` you should see an empty list of services and a reminder
of your current host:

>>> daeploy ls # doctest: +SKIP
Active host: http://your-new-host
MAIN    NAME    VERSION    STATUS    RUNNING
------  ------  ---------  --------  ---------

Changing between hosts
----------------------

As you might have observed, your previous hosts are already listed for you when you
use ``daeploy login``. This is to save you the effort of remembering and repeatedly
typing in the same URLs. Say that we want to change back to http://your-host,
then we can simply call ``daeploy login`` again, and say that we want host 0:

>>> daeploy login # doctest: +SKIP
Current hosts:
0 - http://your-host
1 - http://your-new-host
Enter Daeploy host: 0
Changed host to http://your-new-host
