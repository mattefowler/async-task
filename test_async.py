import time
import traceback
from collections import Counter
from threading import Thread
from unittest import TestCase

from async_task.async_task import Async


class TestAsync(TestCase):
    def test_free_function(self):
        @Async
        def func(a, b):
            return a + b

        self.assertIsInstance(func, Async)
        worker = func(1, b=2)

        self.assertIsInstance(worker, Async.Worker)
        self.assertEqual(3, worker.result)

    def test_exception_transport(self):
        @Async
        def func():
            raise ValueError("Exception Origin")

        with self.assertRaises(ValueError) as exc_ctx:
            try:
                func().wait()
            except ValueError as ve:
                tb = "\n".join(traceback.format_tb(ve.__traceback__))
                raise

        # original traceback is correctly transported across threads
        self.assertIn("""raise ValueError("Exception Origin")""", tb)

    def test_method_decorator(self):
        class Cls:
            @Async[float]
            def foo(self, a: float, b: float) -> float:
                return a + b

        class DCls(Cls):
            @Async[float]
            def foo(self, a, b) -> float:
                return a * b

        self.assertEqual(Cls.foo.__name__, "foo")
        self.assertEqual(3, Cls().foo(1, 2).result)
        self.assertEqual(2, DCls().foo(1, 2).result)

    def test_timeout(self):
        @Async
        def foo():
            time.sleep(0.1)

        with self.assertRaises(TimeoutError):
            foo().wait(0.001)

    def test_threadname(self):
        def foo():
            pass

        name = "foo thread"
        _async = Async(foo, thread_name=name)
        worker = _async()
        self.assertEqual(name, worker._thread.name)
        self.assertEqual(f"Async Worker {name}", str(worker))

    def test_wait_many(self):
        @Async
        def test(sleep_time=0):
            time.sleep(sleep_time)

        with self.assertRaises(ExceptionGroup) as eg:
            Async.wait(test(.1), timeout=0)
        ex, = eg.exception.exceptions
        self.assertIsInstance(ex, TimeoutError)

        with self.subTest("Test combined timeout"):
            @Async
            def _raise():
                raise ValueError("expected")

            with self.assertRaises(ExceptionGroup) as eg:
                Async.wait(test(0), test(.1), test(.1), _raise(), timeout=.05)
                ex_counts = Counter(map(type, eg.exception.exceptions))
                self.assertEqual({TimeoutError: 2, ValueError: 1}, ex_counts)

    def test_daemon(self):

        @Async.daemon
        def f():
            pass

        worker: Async.Worker = f()
        thread: Thread = worker._thread
        self.assertTrue(thread.daemon)

    def test_run_many(self):
        items = []

        def append():
            items.append(0)

        workers = Async.run(append, Async(append))
        Async.wait(*workers)
        self.assertEqual([0, 0], items)
