.. _hosting-static-html-reference:

Host static HTML pages using Daeploy
====================================

A common use case for a service is to host static HTML pages.
For instance, these HTML pages can be usage reports, summaries, welcome pages, or whatever you need and want them to be!

You only need **1** line of code in your service to host your static HTML pages::

    from daeploy import service
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    service.app.mount("/", StaticFiles(directory="my_pages", html=True), name="")

    if __name__ == "__main__":
        service.run()

The folder structure of the above service is:

::

    my_service
    |── .s2i
    |   └── environment
    ├── servcice.py
    ├── requirements.txt
    ├── my_pages     
    │   └── index.html
    │   └── report.html
    └── tests         
        ├── base_functionality_test.py
        └── user_test.py

.. note:: The HTML pages need to be located togheter in a sub-directory. In this example,
    they are located in the ``my_pages`` directory.

The service can be deployed by: 

>>> daeploy deploy my_service 1.0.0 my_service/ # doctest: +SKIP
Active host: http://your-host
Deploying service...
Service deployed successfully
MAIN    NAME         VERSION    STATUS    RUNNING
------  -----------  ---------  --------  -----------------------------------
*       my_service   1.0.0      running   Running (since 2020-12-15 12:10:25)

By going to the following URL, the ``index.html`` page will be loaded:

``http://your-host/services/my_service/``

And to load ``report.html``, go to:

``http://your-host/services/my_service/report.html``
