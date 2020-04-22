import asyncio

import pytest

from async_class import AsyncClassBase


async def test_simple():
    await AsyncClassBase()


async def test_simple_class():
    class Sample(AsyncClassBase):
        event = asyncio.Event()

        async def __ainit__(self):
            loop = asyncio.get_event_loop()
            loop.call_soon(self.event.set)
            await self.event.wait()

    instance = await Sample()

    assert instance.__class__ == Sample

    assert Sample.event.is_set()


async def test_simple_inheritance():
    class Sample(AsyncClassBase):
        event = asyncio.Event()

        async def __ainit__(self):
            loop = asyncio.get_event_loop()
            loop.call_soon(self.event.set)
            await self.event.wait()

    class MySample(Sample):
        async def __ainit__(self):
            await super().__ainit__()

    instance = await MySample()

    assert instance.__class__ == MySample
    assert instance.__class__ != Sample

    assert Sample.event.is_set()
    assert MySample.event.is_set()


async def test_simple_with_init():
    class Sample(AsyncClassBase):
        event = asyncio.Event()

        def __init__(self):
            self.value = 3

        async def __ainit__(self):
            loop = asyncio.get_event_loop()
            loop.call_soon(self.event.set)

            await self.event.wait()

    instance = await Sample()

    assert instance.__class__ == Sample

    assert Sample.event.is_set()
    assert instance.value == 3


async def test_simple_with_init_inheritance():
    class Sample(AsyncClassBase):
        event = asyncio.Event()

        def __init__(self):
            self.value = 3

        async def __ainit__(self):
            loop = asyncio.get_event_loop()
            loop.call_soon(self.event.set)

            await self.event.wait()

    class MySample(Sample):
        pass

    instance = await MySample()

    assert instance.__class__ == MySample

    assert Sample.event.is_set()
    assert MySample.event.is_set()
    assert instance.value == 3


async def test_await_redeclaration():
    with pytest.raises(TypeError):

        class _(AsyncClassBase):
            def __await__(self):
                pass
