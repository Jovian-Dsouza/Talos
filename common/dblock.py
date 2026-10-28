"""Serialize access to a SQLite connection shared by worker threads."""

import functools
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def locked(method: F) -> F:
    """Run a method under the owning object's `_lock` (a threading.RLock)."""

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]
