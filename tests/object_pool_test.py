import errno
import threading
import time

from nose.tools import assert_raises

from zrpc.object_pool import ObjectPool


def test_get_adds_an_object_to_the_pool():
    pool = ObjectPool(object)
    assert len(pool.objects) == 0
    with pool.get() as client:
        pass
    assert len(pool.objects) == 1
    assert pool.objects[0] is client


def test_subsequent_gets_in_a_single_thread_reuse_the_same_object():
    pool = ObjectPool(object)
    with pool.get() as first_client:
        pass
    with pool.get() as second_client:
        pass
    assert first_client is second_client


def test_nested_gets_in_a_single_thread_use_new_objects():
    pool = ObjectPool(object)
    with pool.get() as first_client:
        with pool.get() as second_client:
            pass
    assert first_client is not second_client
    assert len(pool.objects) == 2


def test_concurrent_gets_use_different_objects():
    pool = ObjectPool(object)
    def get_a_client():
        with pool.get() as my_client:
            time.sleep(0.2)

    threads = [threading.Thread(target=get_a_client) for _ in xrange(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(pool.objects) == 2


def test_bounded_nonblocking_gets_raise_EWOULDBLOCK():
    pool = ObjectPool(object, maxsize=1)
    with pool.get() as client1:
        with assert_raises(OSError) as cm:
            with pool.get(blocking=False) as client2:
                pass
        assert cm.exception.errno == errno.EWOULDBLOCK


def test_bounded_concurrent_gets_synchronize_and_use_the_same_object():
    pool = ObjectPool(object, maxsize=1)

    def get_a_client():
        with pool.get() as my_client:
            time.sleep(0.2)

    threads = [threading.Thread(target=get_a_client) for _ in xrange(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(pool.objects) == 1
