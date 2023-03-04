from __future__ import annotations

import sys
from collections.abc import Callable
from functools import wraps
from threading import Thread
from types import TracebackType
from typing import Any, Generic, T

SECONDS = float
EXC_INFO = tuple[Exception, type[Exception], TracebackType]


class Async(Generic[T]):
    def __init__(self, function: Callable[..., T], thread_name=None):
        """
        Create an asynchronous execution wrapper around a callable.
        Args:
            function: the callable object to be executed asynchronously
            thread_name: optional logical name to apply to thread.
        """
        wraps(function)(self)
        self._function = function
        self._thread_name = thread_name or getattr(function, "__name__", str(function))

    def __call__(self, *args, **kwargs) -> Worker[T]:
        """Run the function in a background thread with the arguments provided."""
        return self.Worker[T](self._function, self._thread_name, *args, **kwargs)

    def __get__(self, instance, owner) -> Async[T]:
        """Supports use of Async as a method decorator."""
        return Async[T](
            self._function.__get__(instance, owner), f"{instance}.{self._thread_name}"
        )

    class Worker(Generic[T]):
        def __init__(self, function: Callable[..., T], thread_name, *args, **kwargs):
            """
            A background worker that manages relaying output and exceptions back to the calling thread. This is usually
            created by calling an Async object and not instantiated directly.
            Args:
                function:
                thread_name:
                *args:
                **kwargs:
            """
            self._result: T | None = None
            self._exc_info: EXC_INFO | None = None
            self._function = function
            self._thread = Thread(
                target=self._execute, name=thread_name, args=args, kwargs=kwargs
            )
            self._thread.start()

        def _execute(self, *args, **kwargs):
            try:
                self._result = self._function(*args, **kwargs)
            except Exception:
                self._exc_info = sys.exc_info()

        def wait(self, timeout: SECONDS | None = None):
            """
            Block the calling thread until the background-worker thread completes, or raise a TimeoutError if it does
            not occur within the specified timeout period.
            Args:
                timeout: maximum amount of time to block.
            """
            self._thread.join(timeout)
            if self._thread.is_alive():
                raise TimeoutError()
            if self._exc_info:
                etype, e, tb = self._exc_info
                raise e.with_traceback(tb)

        @property
        def result(self) -> T:
            """
            Returns: The output of the function run in the background thread.
            """
            self.wait()
            return self._result

        def __str__(self):
            return f"Async Worker {self._thread.name}"
