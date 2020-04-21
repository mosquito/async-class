async-class
===========

Adding abillity to write classes with awaitable initialization function.


Example
-------

```python

import asyncio
from async_class import AsyncClass


class MyAsyncClass(AsyncClass):
    async def __ainit__(self):
        future = self.create_future()
        self.loop.call_soon(future.set_result)
        await future


async def main():
    instance = await MyAsyncClass()
    print(instance)


asyncio.run(main())

```


Documentation
=============

Module provides metaclasses and some usefule abstractions for writing async code.


TaskStore
---------

TBD

AsyncClass
----------

Base class with task store instance and helpers for simple task management.

AsyncClassBase
--------------

Is a base wrapper with metaclass has no additional methods and properties like
`self.loop` and `TaskStore` related helpers (`self.create_task`, `self.create_future`).


```python

import asyncio
from async_class import AsyncClassBase


class MyAsyncClass(AsyncClassBase):
    async def __ainit__(self):
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        loop.call_soon(future.set_result)
        await future


async def main():
    instance = await MyAsyncClass()
    print(instance)


asyncio.run(main())

```

