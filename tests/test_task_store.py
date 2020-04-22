import asyncio

import pytest

from async_class import TaskStore


async def test_store_close(loop):
    store = TaskStore()
    task1 = store.create_task(asyncio.sleep(3600))
    future1 = store.create_future()

    child_store = store.get_child()
    task2 = child_store.create_task(asyncio.sleep(3600))
    future2 = child_store.create_future()

    # Bad future
    future3 = loop.create_future()
    child_store.futures.add(future3)

    async def awaiter(f):
        return await f

    # Bad task
    task3 = loop.create_task(awaiter(future3))
    child_store.tasks.add(task3)

    future3.set_result(True)

    await asyncio.sleep(0.1)

    await store.close()
    assert store.closed

    with pytest.raises(asyncio.InvalidStateError):
        await store.close()

    for f in (future1, future2):
        assert isinstance(f.exception(), asyncio.CancelledError)

    futures = (task1, task2, future1, future2)

    assert all(f.done() for f in futures)

    assert await future3
    assert await task3
