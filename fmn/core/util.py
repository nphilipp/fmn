import asyncio
import inspect
from functools import cache, partial
from typing import Any, AsyncIterator, Awaitable, Callable, Iterator, TypeVar

from decorator import decorator

from .config import CashewsTTLTypes, get_settings


def acquire_asyncio_event_loop() -> asyncio.AbstractEventLoop:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    return loop


T = TypeVar("T")


@decorator
def wrap_async_method(func: Callable[..., Awaitable[T]], attrname: str, *args, **kwargs) -> T:
    self, args = args[0], args[1:]
    return acquire_asyncio_event_loop().run_until_complete(
        getattr(self.__wrapped__, attrname)(*args, **kwargs)
    )


STOPPED_SENTINEL = object()


@decorator
def wrap_async_iterator(
    func: Callable[..., AsyncIterator[T]], attrname: str, *args, **kwargs
) -> Iterator[T]:
    self, args = args[0], args[1:]
    async_iterator = getattr(self.__wrapped__, attrname)(*args, **kwargs)

    async def get_next():
        try:
            return await anext(async_iterator)
        except StopAsyncIteration:
            return STOPPED_SENTINEL

    loop = acquire_asyncio_event_loop()

    while (item := loop.run_until_complete(get_next())) is not STOPPED_SENTINEL:
        yield item


@decorator
def wrap_func(func: Callable[..., T], attrname: str, *args, **kwargs) -> T:
    self, args = args[0], args[1:]
    return getattr(self.__wrapped__, attrname)(*args, **kwargs)


def wrap_attribute(attr: Any, attrname: str) -> Any:
    @property
    def wrapped_attribute(self):
        return getattr(self.__wrapped__, attrname)

    return wrapped_attribute


def make_synchronous(cls: type, name: str) -> type:
    """Wrap a class to make its async methods/iterators usable from sync code.

    :param cls:     The class to wrap.
    :param name:    The name of the wrapper class.
    :return:        A new type which wraps `cls`.

    Essentially, it creates an object of the wrapped class and dispatches
    almost everything to it, except function and generator methods marked with
    `async`, which it runs through asyncio.

    As is, this probably doesn’t work for class methods and static methods, or
    generators which accept values being sent into them.
    """

    @decorator
    def wrap_init(func, *args, **kwargs) -> None:
        self, args = args[0], args[1:]
        super(cls, self).__setattr__("__wrapped__", cls(*args, **kwargs))

    def __getattr__(self, attrname: str) -> Any:
        return getattr(self.__wrapped__, attrname)

    def __setattr__(self, attrname: str, value: Any) -> None:
        setattr(self.__wrapped__, attrname, value)

    class_attributes = {
        "__init__": wrap_init(cls.__init__),
        "__getattr__": __getattr__,
        "__setattr__": __setattr__,
    }

    for attrname in dir(cls):
        try:
            attr = getattr(cls, attrname)
        except AttributeError:  # pragma: no cover
            # If the zope.interface package is present, it adds __provides__ to abc.ABC but this
            # raises an AttributeError when accessed.
            continue

        if attrname in ("__module__", "__slots__"):
            class_attributes[attrname] = attr
            continue

        if attrname.startswith("_"):
            continue

        if inspect.iscoroutinefunction(attr):
            class_attributes[attrname] = wrap_async_method(attr, attrname)
        elif inspect.isasyncgenfunction(attr):
            class_attributes[attrname] = wrap_async_iterator(attr, attrname)
        elif callable(attr):
            class_attributes[attrname] = wrap_func(attr, attrname)
        else:
            class_attributes[attrname] = wrap_attribute(attr, attrname)

    return type(name, (cls,), class_attributes)


@cache
def cashews_cache_arg(arg: str, scope: str | None = None) -> Callable[Any, dict]:
    """Generate a cached function for cashews decorator arguments."""

    def get_cashews_cache_arg(arg: str, scope: str | None = None, *args, **kwargs):
        settings = get_settings()

        if scope:
            try:
                return getattr(settings.cache.cashews.args[scope], arg)
            except (AttributeError, KeyError):
                pass

        return getattr(settings.cache.cashews.default_args, arg)

    return cache(partial(get_cashews_cache_arg, arg, scope))


def cashews_cache_ttl(scope: str | None = None) -> Callable[[str | None], CashewsTTLTypes]:
    """Generate a cached function for cashews decorator ttl values."""
    return cashews_cache_arg("ttl", scope)
