import abc
import asyncio
import typing as t
import logging
from functools import wraps
from weakref import WeakSet

try:
    from functools import cached_property, cache
except ImportError:
    from functools import lru_cache

    def cached_property(func):      # type: ignore
        return property(lru_cache(None)(func))

    cache = lru_cache(None)


try:
    from asyncio import get_running_loop
except ImportError:
    def get_running_loop() -> asyncio.AbstractEventLoop:
        loop = asyncio.get_event_loop()
        assert loop.is_running()
        return loop


log = logging.getLogger(__name__)
CloseCallbacksType = t.Callable[[], t.Union[t.Any, t.Coroutine]]


class TaskStore:
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.tasks: t.Set[asyncio.Task] = set()
        self.futures: t.Set[asyncio.Future] = set()
        self.children: t.MutableSet[TaskStore] = WeakSet()
        self.close_callbacks: t.Set[CloseCallbacksType] = set()
        self.__loop = loop
        self.__closing: asyncio.Future = self.__loop.create_future()

    def get_child(self) -> "TaskStore":
        store = self.__class__(self.__loop)
        self.children.add(store)
        return store

    def add_close_callback(self, func: CloseCallbacksType) -> None:
        self.close_callbacks.add(func)

    def create_task(self, *args: t.Any, **kwargs: t.Any) -> asyncio.Task:
        task = self.__loop.create_task(*args, **kwargs)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)
        return task

    def create_future(self) -> asyncio.Future:
        future = self.__loop.create_future()
        self.futures.add(future)
        future.add_done_callback(self.futures.remove)
        return future

    @property
    def is_closed(self) -> bool:
        return self.__closing.done()

    async def close(self, exc: t.Optional[Exception] = None) -> None:
        if self.__closing.done():
            return

        if exc is None:
            self.__closing.set_result(True)
        else:
            self.__closing.set_exception(exc)

        for future in self.futures:
            if future.done():
                continue

            future.set_exception(
                exc or asyncio.CancelledError("Object %r closed" % self),
            )

        tasks: t.List[t.Union[asyncio.Future, t.Coroutine]] = []

        for func in self.close_callbacks:
            try:
                result = func()
            except BaseException:
                log.exception("Error in close callback %r", func)
                continue

            if (
                asyncio.iscoroutine(result) or
                isinstance(result, asyncio.Future)
            ):
                tasks.append(result)

        for task in self.tasks:
            if task.done():
                continue

            task.cancel()
            tasks.append(task)

        for store in self.children:
            tasks.append(store.close())

        await asyncio.gather(*tasks, return_exceptions=True)


class AsyncClassMeta(abc.ABCMeta):
    def __new__(
        cls,
        clsname: str,
        bases: t.Tuple[type, ...],
        namespace: t.Dict[str, t.Any]
    ) -> "AsyncClassMeta":
        instance = super(AsyncClassMeta, cls).__new__(
            cls, clsname, bases, namespace,
        )

        if not asyncio.iscoroutinefunction(instance.__ainit__):  # type: ignore
            raise TypeError("__ainit__ must be coroutine")

        return instance


ArgsType = t.Any
KwargsType = t.Any


class AsyncClassBase(metaclass=AsyncClassMeta):
    __slots__ = ("_args", "_kwargs")
    _args: ArgsType
    _kwargs: KwargsType

    def __new__(cls, *args: t.Any, **kwargs: t.Any) -> "AsyncClassBase":
        self = super().__new__(cls)
        self._args = args
        self._kwargs = kwargs
        return self

    @cached_property
    def loop(self) -> asyncio.AbstractEventLoop:
        return get_running_loop()

    def __await__(self) -> t.Generator[None, t.Any, "AsyncClassBase"]:
        yield from self.__ainit__(*self._args, **self._kwargs).__await__()
        return self

    async def __ainit__(
        self, *args: t.Tuple[t.Any, ...], **kwargs: t.Dict[str, t.Any]
    ) -> t.NoReturn:
        pass


# noinspection PyAttributeOutsideInit
class AsyncClass(AsyncClassBase):
    def __init__(self, *args: ArgsType, **kwargs: KwargsType):
        self.__closed = False
        self._async_class_task_store: TaskStore

    @property
    def __tasks__(self) -> TaskStore:
        return self._async_class_task_store

    @property
    def is_closed(self) -> bool:
        return self.__closed

    def _link_to(self, parent: "AsyncClass") -> None:
        self._async_class_task_store = parent.__tasks__.get_child()
        self.__tasks__.add_close_callback(self.close)

    def create_task(
        self, *args: ArgsType, **kwargs: KwargsType
    ) -> asyncio.Task:
        return self.__tasks__.create_task(*args, **kwargs)

    def create_future(self) -> asyncio.Future:
        return self.__tasks__.create_future()

    async def __adel__(self) -> None:
        pass

    def __init_subclass__(cls, **kwargs: KwargsType):
        if getattr(cls, "__await__") is not AsyncClass.__await__:
            raise TypeError("__await__ redeclaration is forbidden")

    def __await__(self) -> t.Generator[t.Any, None, "AsyncClass"]:
        if not hasattr(self, "_async_class_task_store"):
            self._async_class_task_store = TaskStore(self.loop)

        yield from self.create_task(
            self.__ainit__(*self._args, **self._kwargs)
        ).__await__()
        return self

    def __del__(self) -> None:
        if self.__closed:
            return
        self.close()

    def close(self, exc: t.Optional[Exception] = None) -> t.Awaitable:
        tasks: t.List[t.Union[asyncio.Future, t.Coroutine]] = []

        if hasattr(self, "_async_class_task_store") and not self.__closed:
            tasks.append(self.__adel__())
            tasks.append(self.__tasks__.close(exc))
            self.__closed = True
        return asyncio.gather(*tasks, return_exceptions=True)


T = t.TypeVar("T")

TaskFuncResultType = t.Coroutine[t.Any, None, T]
TaskFuncType = t.Callable[..., TaskFuncResultType]


def task(func: TaskFuncType) -> TaskFuncType:
    @wraps(func)
    async def wrap(
        self: AsyncClass,
        *args: ArgsType,
        **kwargs: KwargsType
    ) -> TaskFuncResultType:
        # noinspection PyCallingNonCallable
        return await self.create_task(func(self, *args, **kwargs))

    return wrap


__all__ = (
    "AsyncClass",
    "AsyncClassBase",
    "TaskStore",
)
