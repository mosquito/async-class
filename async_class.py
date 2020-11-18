import abc
import asyncio
import typing


class TaskStore:
    def __init__(self):
        self.tasks = set()
        self.futures = set()
        self.children = set()
        self.__loop = None
        self.__closed = False

    def get_child(self):
        store = self.__class__()
        self.children.add(store)
        return store

    @property
    def loop(self):
        if self.__loop is None:
            self.__loop = asyncio.get_event_loop()
        return self.__loop

    def create_task(self, *args, **kwargs) -> asyncio.Task:
        task = self.loop.create_task(*args, **kwargs)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)
        return task

    def create_future(self):
        future = self.loop.create_future()
        self.futures.add(future)
        future.add_done_callback(self.futures.remove)
        return future

    @property
    def closed(self):
        return self.__closed

    def close(self) -> typing.Coroutine:
        if self.__closed:
            raise asyncio.InvalidStateError("%r already closed")

        self.__closed = True

        for future in self.futures:
            if future.done():
                continue

            future.set_exception(
                asyncio.CancelledError("Object %r closed" % self),
            )

        tasks = []

        for task in self.tasks:
            if task.done():
                continue

            task.cancel()
            tasks.append(task)

        for store in self.children:
            tasks.append(asyncio.ensure_future(store.close()))

        async def closer():
            await asyncio.gather(*tasks, return_exceptions=True)

        return closer()


class AsyncClassMeta(abc.ABCMeta):
    def __new__(cls, clsname, superclasses, attributedict):
        if "__await__" in attributedict and superclasses:
            raise TypeError("__await__ redeclaration is forbidden")

        instance = super(AsyncClassMeta, cls).__new__(
            cls, clsname, superclasses, attributedict,
        )

        if not asyncio.iscoroutinefunction(instance.__ainit__):
            raise TypeError("__ainit__ must be coroutine")

        return instance


class AsyncClassBase(metaclass=AsyncClassMeta):
    __slots__ = ("_args", "_kwargs")

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._args = args
        self._kwargs = kwargs
        return self

    def __await__(self):
        yield from self.__ainit__(*self._args, **self._kwargs).__await__()
        return self

    async def __ainit__(self, *args, **kwargs):
        pass


class AsyncClass(AsyncClassBase):
    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.__tasks__.loop

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__tasks = TaskStore()
        self.__closed = False

    @property
    def __tasks__(self) -> TaskStore:
        return self.__tasks

    def create_task(self, *args, **kwargs) -> asyncio.Task:
        return self.__tasks__.create_task(*args, **kwargs)

    def create_future(self):
        return self.__tasks__.create_future()

    async def __adel__(self):
        pass

    def __del__(self):
        if self.__closed:
            return

        self.close()

    def close(self) -> asyncio.Task:
        if self.__closed:
            raise asyncio.InvalidStateError

        self.__closed = True

        async def closer():
            done, _ = await asyncio.wait(
                [self.__adel__(), self.__tasks__.close()],
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in done:
                task.result()

        return asyncio.get_event_loop().create_task(closer())


__all__ = (
    "AsyncClass",
    "AsyncClassBase",
    "TaskStore",
)
