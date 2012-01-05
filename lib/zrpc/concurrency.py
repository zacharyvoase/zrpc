"""Utilities for managing concurrency in a sane way."""

from contextlib import contextmanager
import sys
import threading


class Callback(object):

    """
    A threading-based callback supporting both values and exceptions.

    This object mimics the Python coroutine object in supporting :meth:`send`
    and :meth:`throw`, only sending values and throwing exceptions across
    thread boundaries as opposed to between coroutines. It should be used for
    synchronization where more than a typical ``threading.Event`` is needed,
    because values/exceptions need to be associated with those events.
    """

    event_class = threading.Event

    def __init__(self):
        self.event = self.event_class()
        self.value = None
        self.exc_info = None

    def reset(self):
        self.event.clear()
        self.value = None
        self.exc_info = None

    def set(self):
        self.send(None)

    def send(self, value):
        self.value = value
        self.event.set()

    def throw(self, *exc_info):
        if len(exc_info) == 0:
            exc_info = sys.exc_info()
        elif len(exc_info) == 1:
            try:
                raise exc_info[0]
            except Exception:
                exc_info = sys.exc_info()
        elif len(exc_info) == 3:
            pass
        else:
            raise TypeError("Invalid exception argument: %r" % (exc_info,))

        self.exc_info = exc_info
        self.event.set()

    @property
    def catch_exceptions(self):
        @contextmanager
        def exception_catcher(die=True):
            try:
                yield
            except Exception, exc:
                self.throw(*sys.exc_info())
                if die:
                    raise SystemExit  # Kill the current thread quietly.
                raise  # Raise the original error.
        return exception_catcher

    def wait(self):
        self.event.wait()
        if self.exc_info:
            raise self.exc_info[1]
        return self.value


class DummyCallback(Callback):

    """A null callback which never does anything."""

    event_class = object

    def throw(self, *args):
        pass

    def send(self, value):
        pass

    def wait(self):
        return None
