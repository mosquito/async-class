import asyncio

import pytest

from async_class import AsyncClass, TaskStore


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

    with pytest.raises(asyncio.InvalidStateError):
        await obj.close()

    del obj
