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

    The :meth:`spawn` and :meth:`die` methods, and the :attr:`event_class`
    attribute can be overridden in subclasses to support alternative,
    thread-like concurrency models (e.g. gevent, eventlet, etc.).
    """

    event_class = threading.Event

    def __init__(self):
        self.event = self.event_class()
        self.value = None
        self.exc_info = None

    def spawn(self, func, args=(), kwargs=None, **opts):

        """
        Abstract method for spawning a function in a new thread.

        The returned object should represent the thread, and have at least a
        ``join()`` method.
        """

        thread = threading.Thread(target=func, args=args,
                                  kwargs=(kwargs or {}))
        thread.daemon = opts.get('daemon', False)
        thread.start()
        return thread

    def reset(self):
        """Reset this callback, allowing it to be used again."""

        self.event.clear()
        self.value = None
        self.exc_info = None

    def set(self):
        """Alias for ``send(None)``."""

        self.send(None)

    def send(self, value):
        """Pass the provided value to the waiting thread."""

        self.value = value
        self.event.set()

    def throw(self, *exc_info):

        """
        Throw the given exception in the waiting thread.

        There are three valid ways of calling this method:

        * No arguments: use ``sys.exc_info()`` as the source of the exception.
        * 1 argument: an exception object. This is raised and immediately
          caught so as to capture a traceback.
        * 3 arguments: interpreted as the three parts of a ``sys.exc_info()``
          tuple.
        """

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
        """A context manager to catch and throw unhandled exceptions."""

        @contextmanager
        def exception_catcher(die=True):
            try:
                yield
            except Exception, exc:
                self.throw()
                if die:
                    self.die()
                else:
                    raise
        return exception_catcher

    def die(self):
        """Abstract method to kill the current thread."""

        raise SystemExit

    def wait(self):
        """Wait for the callback to be called, and return/raise."""

        self.event.wait()
        if self.exc_info:
            raise self.exc_info[1]
        return self.value


class DummyCallback(Callback):

    """A null callback which does nothing."""

    event_class = object

    def throw(self, *args):
        pass

    def send(self, value):
        pass

    def wait(self):
        pass

    def die(self):
        pass


try:
    import gevent.event
except ImportError:
    pass
else:
    class GeventCallback(Callback):
        """A callback class supporting gevent instead of threading."""

        event_class = gevent.event.Event
        die_exception = gevent.GreenletExit

        def spawn(self, func, args=(), kwargs=None, **opts):
            return gevent.spawn(func, *args, **(kwargs or {}))
