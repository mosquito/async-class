import asyncio
import gc

import pytest

from async_class import AsyncObject, TaskStore, link, task


class GlobalInitializedClass(AsyncObject):
    pass


global_initialized_instance = GlobalInitializedClass()


async def test_global_initialized_instance(loop):
    await global_initialized_instance
    assert not global_initialized_instance.is_closed


async def test_simple():
    await AsyncObject()


async def test_simple_class():
    class Simple(AsyncObject):
        event = asyncio.Event()

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    instance = await Simple()

    assert instance.__class__ == Simple

    assert Simple.event.is_set()


async def test_simple_inheritance():
    class Simple(AsyncObject):
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
    class Simple(AsyncObject):
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
    class Simple(AsyncObject):
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

        class _(AsyncObject):
            def __ainit__(self):
                pass


async def test_async_class_task_store():
    class Sample(AsyncObject):
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
    class Parent(AsyncObject):
        pass

    class Child(Parent):
        async def __ainit__(self, parent: Parent):
            link(self, parent)

    parent = await Parent()
    child = await Child(parent)
    assert not child.is_closed
    await parent.close(asyncio.CancelledError)
    assert parent.is_closed
    assert parent.__tasks__.is_closed
    assert child.__tasks__.is_closed
    assert child.is_closed


async def test_await_redeclaration():
    with pytest.raises(TypeError):

        class _(AsyncObject):
            def __await__(self):
                pass


async def test_close_uninitialized(loop):
    future = asyncio.Future()

    class Sample(AsyncObject):
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


def callback_regular():
    pass


def callback_with_raise():
    return 1 / 0


@pytest.mark.parametrize("callback", [callback_regular, callback_with_raise])
async def test_close_callabacks(callback):
    class Sample(AsyncObject):
        pass

    instance = await Sample()
    event = asyncio.Event()
    instance.__tasks__.add_close_callback(event.set)
    instance.__tasks__.add_close_callback(callback)
    await instance.close()
    assert event.is_set()


async def test_del():
    class Sample(AsyncObject):
        pass

    instance = await Sample()
    event = asyncio.Event()
    instance.__tasks__.add_close_callback(event.set)
    del instance
    await event.wait()


async def test_del_child():
    class Parent(AsyncObject):
        pass

    class Child(Parent):
        async def __ainit__(self, parent: Parent):
            link(self, parent)

    parent = await Parent()

    parent_event = asyncio.Event()
    parent.__tasks__.add_close_callback(parent_event.set)

    child = await Child(parent)

    child_event = asyncio.Event()
    child.__tasks__.add_close_callback(child_event.set)

    del child

    for generation in range(3):
        gc.collect(generation)

    await child_event.wait()
    assert not parent_event.is_set()


async def test_link_init():
    class Parent(AsyncObject):
        pass

    class Child(Parent):
        def __init__(self, parent: Parent):
            super().__init__()
            link(self, parent)

    parent = await Parent()

    parent_event = asyncio.Event()
    parent.__tasks__.add_close_callback(parent_event.set)

    child = await Child(parent)

    child_event = asyncio.Event()
    child.__tasks__.add_close_callback(child_event.set)

    del child

    for generation in range(3):
        gc.collect(generation)

    await child_event.wait()
    assert not parent_event.is_set()


async def test_close_non_initialized():
    class Sample(AsyncObject):
        pass

    sample = Sample()
    await sample.close()


async def task_decorator():
    class Sample(AsyncObject):
        @task
        async def sleep(self, *args):
            return await asyncio.sleep(*args)

    sample = await Sample()
    result = sample.sleep(0)

    assert isinstance(result, asyncio.Task)
    result.cancel()

    with pytest.raises(asyncio.CancelledError):
        await result

    await sample.sleep(0)
