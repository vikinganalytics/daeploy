.. _plotly-dash-service-reference:

Using Plotly Dash to build a dashboard
======================================

In this tutorial we will see how to create a service that serves a dashboard using
`Plotly Dash <https://plotly.com/dash/>`_.We will not go into detail into how
to use Plotly Dash itself, but rather how to deploy a Plotly Dash application with Daeploy.

Example Plotly Dash application
-------------------------------

We will use a `hello-world` Plotly Dash application in this tutorial that simply prints
`Hello World`. The code for this application looks like this::

    import dash
    import dash_html_components as html

    app = dash.Dash(__name__)

    app.layout = html.Div(
        children=[
            html.H1(children="Hello World"),
        ]
    )

    if __name__ == "__main__":
        app.run_server(debug=True)

In order to run this application, our `requirements.txt` will look like::

    dash

That is all you need to run this Plotly Dash application locally. Lets now have a
look at making this example deployable and runnable with Daeploy.

Plotly Dash application as a standalone service
-----------------------------------------------

Let's get som fresh boiler-plate directories/files using the functionality provided
by the Daeploy CLI:

>>> daeploy init # doctest: +SKIP
project_name [my_project]: plotly_dashboard

To run the same dashboard on Daeploy only a few changes have to be made. First, when
creating the app-object we must tell Dash that it will be running under
some custom root_path (aka base_path):

.. literalinclude:: ../../../../examples/dash_services/plotly_dashboard/service.py
    :lines: 3-8

And when starting the server, we need to make sure that the Plotly Dash application
accepts connections from others than localhost:

.. literalinclude:: ../../../../examples/dash_services/plotly_dashboard/service.py
    :lines: 16-17

The final application code should now look like this:

.. literalinclude:: ../../../../examples/dash_services/plotly_dashboard/service.py

We can now deploy the Plotly Dash app, like we would any other service, with one important
difference. Plotly Dash, by default, use port 8050 to communicate so we have to explicitly
set the port when deploying:

>>> daeploy deploy plotly_dashboard 1.0.0 ./plotly_dashboard --port 8050 # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME              VERSION    STATUS    RUNNING
------  ----------------  ---------  --------  -----------------------------------
*       plotly_dashboard  1.0.0      running   Running (since 2021-01-13 07:14:55)

.. note:: Daeploy services created using the SDK use port 8000, which is the default
    port for ``daeploy deploy``. But when deploying other apps it might be necessary
    to change it to not get a `Bad Gateway`.

Open http://your-host/services/plotly_dashboard/ and you should see your app there


Plotly Dash application as part of a SDK-based application
----------------------------------------------------------

It is also possible to add a Plotly Dash application as a (sub-)part of an SDK-based
service. This is done by mounting the Plotly Dash ``server`` on the SDK ``app``. In the
example below, we mount the Plotly Dash ``app`` at the subpath ``/dashboard/`` under the
Daeploy SDK service ``app``:

.. literalinclude:: ../../../../examples/dash_services/plotly_dashboard_sdk/service.py


Assuming we deploy our service as such (note that we no longer need to specify a custom
port number since we are using the SDK to actually run the application):

>>> daeploy deploy plotly_dashboard 1.0.0 ./plotly_dashboard # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME              VERSION    STATUS    RUNNING
------  ----------------  ---------  --------  -----------------------------------
*       plotly_dashboard  1.0.0      running   Running (since 2021-01-13 07:14:55)

Your dashboard would then be available at http://your-host/services/plotly_dashboard/dashboard/