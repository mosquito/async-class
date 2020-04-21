import abc
import asyncio
import typing
from collections.abc import Awaitable


def is_async_class_wrapper(obj):
    return hasattr(obj, "__is_async_class_wrapper__")


def unwrap_async_class(obj):
    return getattr(obj, "__async_class__")


class TasksStore:
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

    def close(self) -> typing.Coroutine:
        if self.__closed:
            raise asyncio.InvalidStateError("%r already closed")

        self.__closed = True

        for future in self.futures:
            if future.done():
                continue
            future.set_exception(
                asyncio.CancelledError("Object %r closed" % self)
            )

        tasks = []

        for task in self.tasks:
            if task.done():
                continue
            task.cancel()
            tasks.append(task)

        for store in self.children:
            tasks.append(store.close())

        async def closer():
            await asyncio.gather(*tasks, return_exceptions=True)

        return closer()


class AsyncClassMeta(abc.ABCMeta):
    @staticmethod
    def wrapper_init(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    @staticmethod
    def wrapper_await(self):
        instance = self.__async_class__(*self._args, **self._kwargs)
        yield from instance.__ainit__(*self._args, **self._kwargs).__await__()
        return instance

    def __new__(cls, clsname, superclasses, attributedict):
        real_superclasses = []
        for superclass in superclasses:
            if is_async_class_wrapper(superclass):
                superclass = unwrap_async_class(superclass)

            real_superclasses.append(superclass)

        async_instance = super(AsyncClassMeta, cls).__new__(
            cls, clsname, tuple(real_superclasses), attributedict
        )

        if not asyncio.iscoroutinefunction(async_instance.__ainit__):
            raise TypeError("__ainit__ must be coroutine")

        wrapper_attributes = {
            "__is_async_class_wrapper__": True,
            "__async_class__": async_instance,
            "__await__": cls.wrapper_await,
            "__init__": cls.wrapper_init,
        }

        class_wrapper = super(AsyncClassMeta, cls).__new__(
            cls, clsname + "AsyncWrapper", (async_instance,),
            wrapper_attributes,
        )

        return class_wrapper


class AsyncClassBase(Awaitable, metaclass=AsyncClassMeta):
    async def __ainit__(self):
        pass

    def __await__(self):
        return


class AsyncClass(AsyncClassBase):
    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self.__tasks__.loop

    def __init__(self):
        self.__tasks__ = TasksStore()

    def create_task(self, *args, **kwargs) -> asyncio.Task:
        return self.__tasks__.create_task(*args, **kwargs)

    def create_future(self):
        return self.__tasks__.create_future()

    async def __adel__(self):
        pass

    def __del__(self):
        self.close()

    def close(self) -> asyncio.Task:
        async def closer():
            done, _ = await asyncio.wait(
                [self.__adel__(), self.__tasks__.close()],
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in done:
                task.result()

        return self.loop.create_task(closer())
