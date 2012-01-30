from collections import deque
from contextlib import contextmanager
import errno
import os
import threading


class ObjectPool(object):

    """
    A generic object pool class for re-using long-lived objects.

    This class is useful for limiting the number of
    :class:`~zrpc.client.Client` connections made by a single process. An
    object pool is simply a semaphore over a pool of objects, optionally
    bounded in size. When an object is requested but there are none available,
    a new one is created using the user-provided factory function, and this is
    returned inside a ``with`` block. When the caller is done with the object,
    it is re-added to the pool, ready to be given to someone else.
    """

    def __init__(self, factory, maxsize=None, semaphore=None, lock=None):

        """
        Create a new object pool.

        :param factory:
            A 0-ary function returning new objects. e.g.:
            ``lambda: Client('tcp://...')``.

        :param maxsize:
            A maximum size for this object pool to grow to. Requests for
            objects above this limit will block until an object has been
            returned to the pool. If unspecified, the pool will be unbounded.

        :param semaphore:
            Pass a semaphore object rather than having the pool create one
            itself. If provided, the ``maxsize`` parameter will be ignored.
            The given object must provide the context manager interface for
            acquisition/release.

        :param lock:
            A lock object (used for modifying the underlying pool); normally
            ``ObjectPool`` will create a ``threading.Lock`` but you can provide
            your own with this parameter. It must provide the context manager
            interface.
        """

        if semaphore is not None:
            self.semaphore = semaphore
        else:
            if maxsize is None:
                maxsize = float('inf')
            self.semaphore = threading.Semaphore(maxsize)

        self.object_lock = lock or threading.Lock()
        self.factory = factory
        self.objects = deque()

    @contextmanager
    def get(self, blocking=True):

        """
        Get an object from the pool, returning it after the end of the block.

        This method is a context manager for temporarily checking an object out
        of the pool. Usage is simple:

            >>> with pool.get() as obj:
            ...     # do something with obj

        You can also run this in non-blocking mode; just pass
        ``blocking=False`` and it will raise an ``OSError`` (with an error
        number of ``errno.EWOULDBLOCK``).
        """

        with acquiring(self.semaphore, blocking):
            with acquiring(self.object_lock, blocking):
                if self.objects:
                    obj = self.objects.popleft()
                else:
                    obj = self.factory()
            yield obj
            self.objects.append(obj)


try:
    import gevent.coros
except ImportError:
    pass
else:
    class GeventObjectPool(ObjectPool):

        """An :class:`ObjectPool` using gevent synchronization primitives."""

        def __init__(self, factory, maxsize=None):
            lock = gevent.coros.RLock()
            if maxsize is None:
                semaphore = gevent.coros.DummySemaphore()
            else:
                semaphore = gevent.coros.Semaphore(maxsize)
            super(GeventObjectPool, self).__init__(factory, lock=lock,
                                                   semaphore=semaphore)


@contextmanager
def acquiring(sync_primitive, blocking=True):

    """
    Context manager for acquiring synchronisation primitives.

    If non-blocking mode is specified, and acquisition of the passed object
    would block, this context manager will raise an ``OSError`` with an error
    number of ``errno.EWOULDBLOCK``.
    """

    acquired = sync_primitive.acquire(blocking)
    if (not blocking) and (not acquired):
        raise OSError(errno.EWOULDBLOCK, os.strerror(errno.EWOULDBLOCK))
    try:
        yield
    finally:
        sync_primitive.release()
