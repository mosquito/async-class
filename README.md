async-class
===========

![PyPI - License](https://img.shields.io/pypi/l/async-class) ![Wheel](https://img.shields.io/pypi/wheel/async-class) ![PyPI](https://img.shields.io/pypi/v/async-class) ![PyPI](https://img.shields.io/pypi/pyversions/async-class)

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

Module provides useful abstractions for writing async code.


`TaskStore`
-----------

`TaskStore` is a task management helper. One instance has `create_task()`
and `create_future()` methods and all created entities will be destroyed
when `TaskStore` will be closed via `close()` method.

Also, a task store might create a linked copy of the self, which will be
closed when the parent instance will be closed.


```python
import asyncio
from async_class import TaskStore


async def main():
    store = TaskStore()
    task1 = store.create_task(asyncio.sleep(3600))

    child_store = store.get_child()
    task2 = child_store.create_task(asyncio.sleep(3600))

    await store.close()

    assert task1.done() and task2.done()


asyncio.run(main())

```

AsyncClass
----------

Base class with task store instance and helpers for simple task management.

```python

import asyncio
from async_class import AsyncClass


class MyClass(AsyncClass):
    def __ainit__(self):
        self.task = self.create_task(asyncio.sleep(3600))


async def main():
    obj = await MyClass()

    assert not obj.task.done()

    await obj.close()

    assert obj.task.done()


asyncio.run(main())
```

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

