from contextlib import contextmanager
import threading

from nose.tools import assert_raises

from zrpc.concurrency import Callback


class SomeError(Exception):
    """An error class just for testing purposes."""
    pass


@contextmanager
def run_thread(func, *args, **kwargs):
    t = threading.Thread(target=func, args=args, kwargs=kwargs)
    t.start()
    try:
        yield t
    finally:
        t.join()


def test_callback_returns_values():
    cb = Callback()
    def return_value(callback):
        callback.send(123)
    with run_thread(return_value, cb):
        assert cb.wait() == 123


def test_callback_throws_errors():
    cb = Callback()
    def throw_error(callback):
        callback.throw(SomeError("ABC"))
    with run_thread(throw_error, cb):
        assert_raises(SomeError, cb.wait)


def test_catch_exceptions_throws_any_unhandled_exceptions_in_waiting_thread():
    cb = Callback()
    def catch_exception(callback):
        with callback.catch_exceptions():
            raise SomeError("ABC")
    with run_thread(catch_exception, cb):
        assert_raises(SomeError, cb.wait)


def test_catch_exceptions_without_die_arg_propagates_exceptions_in_both_threads():
    cb = Callback()
    success = [False]
    def catch_exception_without_dying(callback):
        with assert_raises(SomeError):
            with callback.catch_exceptions(die=False):
                raise SomeError("ABC")
        success[0] = True
    with run_thread(catch_exception_without_dying, cb):
        assert_raises(SomeError, cb.wait)
    assert success[0], "Exception wasn't raised within the original thread"


def test_reset_allows_a_callback_to_be_used_again():
    cb = Callback()
    def return_value(callback):
        callback.send(123)
    with run_thread(return_value, cb):
        assert cb.wait() == 123

    cb.reset()

    def return_value2(callback):
        callback.send(456)
    with run_thread(return_value2, cb):
        assert cb.wait() == 456
