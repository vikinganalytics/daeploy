.. _ticker:

Schedule Repeating Actions
==========================

Every now and then you reach the point where you need some part of your code to be called 
continuously at a certain interval. May it be every second, 24 hours or two months.

For this, Daeploy contain the `call_every` decorator that can be used as such

.. testcode::

    from daeploy import service

    @service.call_every(seconds=60)
    def heartbeat():
        # do something every minute
        pass

    if __name__ == '__main__':
        service.run()

By using this decorator, Daeploy will take care of calling your decorated fuction at the specified interval. 
Note that the decorated function are not allowed to take any arguments. `functools.partial` may be used to 
adhere to this requirement.

