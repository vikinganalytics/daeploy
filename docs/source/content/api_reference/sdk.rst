.. _sdk-reference:

Software Development Kit
========================

Service API (:py:mod:`daeploy.service`)
-----------------------------------

.. note:: :py:mod:`daeploy.service` is an object (not a module), and should be used accordingly.

.. attribute:: daeploy.service

   .. autofunction:: daeploy._service._Service.entrypoint
   .. autofunction:: daeploy._service._Service.store
   .. autofunction:: daeploy._service._Service.call_every
   .. autofunction:: daeploy._service._Service.get_parameter
   .. autofunction:: daeploy._service._Service.add_parameter
   .. autofunction:: daeploy._service._Service.run


Communication API (:py:mod:`daeploy.communication`)
-----------------------------------------------

.. automodule:: daeploy.communication
   :members: notify, Severity, call_service
   :undoc-members:
   :show-inheritance:

Utilities API (:py:mod:`daeploy.utilities`)
-------------------------------------------------

.. automodule:: daeploy.utilities
   :members:
   :undoc-members:
   :show-inheritance:


Data Types API (:py:mod:`daeploy.data_types`)
-------------------------------------------------

.. automodule:: daeploy.data_types
   :members:
   :undoc-members:
   :show-inheritance:
