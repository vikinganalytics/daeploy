.. _connecting-reference:

Before looking into connecting Daeploy with other tools we recommend you to have a look at the
:ref:`monitoring-reference` section.

Connecting Daeploy with Other Tools
===================================

MultiViz Explorer
-----------------
`MultiViz Explorer <https://vikinganalytics.se/multiviz/>`_, is a very powerful tool for data exploration and
it is part of the MultiViz family. The connection between MultiViz Explorer and Daeploy is very simple.

With this connection, you can subscribe to time-series data of your monitored variables.
This connection is handled by a separate and independent service, called mv_connector, which needs to be deployed besides your already deployed services.
The easiest way to deploy the mv_connector service is to run: 

>>> daeploy deploy mv_connector 1.0.0 -g https://github.com/vikinganalytics/mvi-mvx-connector # doctest: +SKIP

For the mv_connector service a few daeploy parameters need to be set: 

- ``multiviz_api_url`` : URL to the API of running multiviz instance.
- ``multiviz_token`` : Access token for MultiViz.
- ``project_id`` : The ID of the project in MV to which the data files should be uploaded into.
- ``service`` : The name of the Daeploy service to fetch time-series data from.
- ``version`` : The version of the Daeploy service to fetch time-series data from. 

You can read about how to change the values of daeploy paramters in 
the :ref:`custom-service_defining_parameters-reference` section. 
