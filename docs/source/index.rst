.. Daeploy documentation master file, created by
   sphinx-quickstart on Tue Oct 27 10:12:38 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to the Daeploy documentation!
=====================================

Daeploy is a software deployment tool that is perfect for
smaller applications where Time-to-Market and ease of use is more important than
scalability to tens of thousands of users and requests.

Daeploy strives to make writing and deploying services (small applications) as quick
and easy as possible without requiring much, or any, prior knowledge
and experience. We want Data Scientists and Algorithm Engineers to spend their time
doing what they love and less time writing `flask` API:s and `dockerfiles`.

Viking Analytics AB
^^^^^^^^^^^^^^^^^^^

Daeploy is developed by Viking Analytics AB. Viking Analytics is a
computer software and services company founded in 2017 and headquartered in
Gothenburg, Sweden. Our vision is to enable our customers to unlock the potential
in their data. For more information, head to our homepage https://vikinganalytics.se/.
If you want to get in contact, you can reach us at info@vikinganalytics.se 


.. toctree::
   :maxdepth: 1
   :caption: Overview

   content/overview/daeploy_description

.. toctree::
   :maxdepth: 1
   :caption: User Guide

   content/getting_started/getting_started
   content/getting_started/custom_service
   content/getting_started/dashboard
   content/getting_started/service_logs
   content/getting_started/autodocs
   content/getting_started/shadow_deployment
   content/getting_started/reaching_service_from_external_applications
   content/getting_started/ticker
   content/getting_started/monitoring
   content/getting_started/cross_service_communication

.. toctree::
   :maxdepth: 1
   :caption: Advanced User Guide

   content/advanced_tutorials/sdk_typing
   content/advanced_tutorials/using_multiple_hosts
   content/advanced_tutorials/email_notifications
   content/advanced_tutorials/manager_api
   content/advanced_tutorials/adv_deploy
   content/advanced_tutorials/cli_autocompletion
   content/advanced_tutorials/service_environment
   content/advanced_tutorials/manager_configuration
   content/advanced_tutorials/testing_services
   content/advanced_tutorials/proxy_dashboard
   content/advanced_tutorials/upload_image
   content/advanced_tutorials/status_codes
   content/advanced_tutorials/integration_with_other_tools
   content/advanced_tutorials/going_beyond_sdk
   content/advanced_tutorials/daeploy_notebook_service

.. toctree::
   :maxdepth: 1
   :caption: Special Usecases

   content/special_usecases/deploying_ml_model
   content/special_usecases/ui_streamlit
   content/special_usecases/ui_plotly_dash
   content/special_usecases/conda
   content/special_usecases/gpu_services
   content/special_usecases/hosting_static_html

.. toctree::
   :glob:
   :maxdepth: 1
   :caption: Api Reference
   
   content/api_reference/cli.rst
   content/api_reference/sdk.rst

.. toctree::
   :maxdepth: 1
   :caption: About

   content/3rd_party_software.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
