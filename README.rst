.. image:: https://coveralls.io/repos/github/mosquito/aiormq/badge.svg?branch=master
   :target: https://coveralls.io/github/mosquito/async-class?branch=master
   :alt: Coveralls

.. image:: https://img.shields.io/pypi/l/async-class
   :target: https://pypi.org/project/async-class
   :alt: License

.. image:: https://github.com/mosquito/async-class/workflows/tests/badge.svg
   :target: https://github.com/mosquito/async-class/actions?query=workflow%3Atests
   :alt: Build status

.. image:: https://img.shields.io/pypi/wheel/async-class
   :target: https://pypi.python.org/pypi/async-class/
   :alt: Wheel

.. image:: https://img.shields.io/pypi/v/async-class
   :target: https://pypi.org/project/async-class
   :alt: Latest version


async-class
===========

Adding abillity to write classes with awaitable initialization function.

.. contents:: Table of contents

Usage example
=============

.. code:: python
    :name: test_simple

    import asyncio
    from async_class import AsyncClass, AsyncObject, task, link


    class MyAsyncClass(AsyncClass):
         async def __ainit__(self):
              # Do async staff here
              pass


    class MainClass(AsyncObject):
         async def __ainit__(self):
              # Do async staff here
              pass

         async def __adel__(self):
              """ This method will be called when object will be closed """
              pass


    class RelatedClass(AsyncObject):
         async def __ainit__(self, parent: MainClass):
              link(self, parent)


    async def main():
         instance = await MyAsyncClass()
         print(instance)

         main_instance = await MainClass()
         related_instance = await RelatedClass(main_instance)

         assert not main_instance.is_closed
         assert not related_instance.is_closed

         await main_instance.close()
         assert main_instance.is_closed

         # will be closed because linked to closed main_instance
         assert related_instance.is_closed

    asyncio.run(main())


Documentation
=============

Async objects might be created when no one event loop has been running.
``self.loop`` property is lazily evaluated.

Module provides useful abstractions for writing async code.

Objects inherited from ``AsyncClass`` might have their own ``__init__``
method, but it strictly not recommend.

Class ``AsyncClass``
--------------------

Is a base wrapper with metaclass has no ``TaskStore`` instance and
additional methods like ``self.create_task`` and ``self.create_future``.

This class just solves the initialization problem:

.. code:: python
    :name: test_async_class

    import asyncio
    from async_class import AsyncClass


    class MyAsyncClass(AsyncClass):
       async def __ainit__(self):
           future = self.loop.create_future()
           self.loop.call_soon(future.set_result, True)
           await future


    async def main():
       instance = await MyAsyncClass()
       print(instance)

    asyncio.run(main())


Class ``AsyncObject``
-------------------------

Base class with task store instance and helpers for simple task
management.

.. code:: python
    :name: test_async_object

    import asyncio
    from async_class import AsyncObject


    class MyClass(AsyncObject):
       async def __ainit__(self):
           self.task = self.create_task(asyncio.sleep(3600))


    async def main():
       obj = await MyClass()

       assert not obj.task.done()

       await obj.close()

       assert obj.task.done()


    asyncio.run(main())


Class ``TaskStore``
-------------------

``TaskStore`` is a task management helper. One instance has
``create_task()`` and ``create_future()`` methods and all created
entities will be destroyed when ``TaskStore`` will be closed via
``close()`` method.

Also, a task store might create a linked copy of the self, which will be
closed when the parent instance will be closed.

.. code:: python
    :name: test_tasK_store

    import asyncio
    from async_class import TaskStore


    async def main():
       store = TaskStore(asyncio.get_event_loop())

       task1 = store.create_task(asyncio.sleep(3600))

       child_store = store.get_child()
       task2 = child_store.create_task(asyncio.sleep(3600))

       await store.close()

       assert task1.done() and task2.done()


    asyncio.run(main())
