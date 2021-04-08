.. _beyond-sdk-reference:

Going Beyond the SDK
====================

Increased API Design Freedom
----------------------------

The SDK :ref:`sdk-reference` is built on top of 
`FastAPI <https://fastapi.tiangolo.com/>`_, which is an open source web framework.
So everything that can be done with the SDK can also be done with FastAPI, or any
other web framework, but with more effort.

To use FastAPI with Daeploy you can use the :obj:`app` object in :py:mod:`daeploy.service`.
Some very basic boilerplate to do this could be


.. testcode::

    from daeploy import service
    
    app = service.app

    # Your code

    if __name__ == '__main__':
        service.run()
