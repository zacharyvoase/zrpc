import errno

import gevent
from nose.tools import assert_raises

from zrpc.object_pool import GeventObjectPool


def test_concurrent_gets_use_different_objects():
    pool = GeventObjectPool(object)
    def get_a_client():
        with pool.get() as my_client:
            gevent.sleep(0.2)

    greenlets = [gevent.spawn(get_a_client) for _ in xrange(2)]
    gevent.joinall(greenlets)
    assert len(pool.objects) == 2


def test_bounded_concurrent_gets_synchronize_and_use_the_same_object():
    pool = GeventObjectPool(object, maxsize=1)

    def get_a_client():
        with pool.get() as my_client:
            gevent.sleep(0.2)

    greenlets = [gevent.spawn(get_a_client) for _ in xrange(2)]
    gevent.joinall(greenlets)
    assert len(pool.objects) == 1


def test_bounded_nonblocking_gets_raise_EWOULDBLOCK():
    pool = GeventObjectPool(object, maxsize=1)
    with pool.get() as client1:
        with assert_raises(OSError) as cm:
            with pool.get(blocking=False) as client2:
                pass
        assert cm.exception.errno == errno.EWOULDBLOCK
