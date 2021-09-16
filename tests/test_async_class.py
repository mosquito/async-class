import asyncio

import pytest

from async_class import AsyncClass, TaskStore


class GlobalInitializedClass(AsyncClass):
    pass


global_initialized_instance = GlobalInitializedClass()


async def test_global_initialized_instance(loop):
    await global_initialized_instance
    assert not global_initialized_instance.is_closed


async def test_simple():
    await AsyncClass()


async def test_simple_class():
    class Simple(AsyncClass):
        event = asyncio.Event()

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    instance = await Simple()

    assert instance.__class__ == Simple

    assert Simple.event.is_set()


async def test_simple_inheritance():
    class Simple(AsyncClass):
        event = asyncio.Event()

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

        def __del__(self):
            return super().__del__()

    class MySimple(Simple):
        pass

    instance = await MySimple()

    assert instance.__class__ == MySimple
    assert instance.__class__ != Simple

    assert Simple.event.is_set()
    assert MySimple.event.is_set()


async def test_simple_with_init():
    class Simple(AsyncClass):
        event = asyncio.Event()

        def __init__(self):
            super().__init__()
            self.value = 3

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    instance = await Simple()

    assert instance.__class__ == Simple

    assert Simple.event.is_set()
    assert instance.value == 3


async def test_simple_with_init_inheritance():
    class Simple(AsyncClass):
        event = asyncio.Event()

        def __init__(self):
            super().__init__()
            self.value = 3

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    class MySimple(Simple):
        pass

    instance = await MySimple()

    assert instance.__class__ == MySimple

    assert Simple.event.is_set()
    assert MySimple.event.is_set()
    assert instance.value == 3


async def test_non_corotine_ainit():
    with pytest.raises(TypeError):

        class _(AsyncClass):
            def __ainit__(self):
                pass


async def test_async_class_task_store():
    class Sample(AsyncClass):
        async def __ainit__(self):
            self.future = self.create_future()
            self.task = self.create_task(asyncio.sleep(3600))

    obj = await Sample()

    assert obj.__tasks__
    assert isinstance(obj.__tasks__, TaskStore)

    assert not obj.future.done()
    assert not obj.task.done()

    await obj.close()

    assert obj.future.done()
    assert obj.task.done()

    assert obj.is_closed
    await obj.close()

    del obj


async def test_async_class_inherit_from():
    class Parent(AsyncClass):
        pass

    class Child(Parent):
        async def __ainit__(self, parent: Parent):
            self._link_to(parent)

    parent = await Parent()
    child = await Child(parent)
    assert not child.is_closed
    await parent.close()
    assert parent.is_closed
    assert parent.__tasks__.is_closed
    assert child.__tasks__.is_closed
    assert child.is_closed


async def test_await_redeclaration():
    with pytest.raises(TypeError):

        class _(AsyncClass):
            def __await__(self):
                pass


async def test_close_uninitialized(loop):
    future = asyncio.Future()

    class Sample(AsyncClass):
        async def __ainit__(self, *args, **kwargs):
            await future

    instance = Sample()

    task: asyncio.Task = loop.create_task(instance.__await__())
    await asyncio.sleep(0.1)

    await instance.close()

    assert task.done()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert future.done()
    with pytest.raises(asyncio.CancelledError):
        await future
