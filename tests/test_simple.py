import asyncio
from async_class import AsyncClass


async def test_simple():
    class Simple(AsyncClass):
        event = asyncio.Event()

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    instance = await Simple()

    assert instance.__class__ != Simple

    assert Simple.event.is_set()


async def test_simple_inheritance():
    class Simple(AsyncClass):
        event = asyncio.Event()

        async def __ainit__(self):
            self.loop.call_soon(self.event.set)
            await self.event.wait()

    class MySimple(Simple):
        pass

    instance = await MySimple()

    assert instance.__class__ != MySimple
    assert instance.__class__ != Simple

    assert MySimple.event.is_set()
