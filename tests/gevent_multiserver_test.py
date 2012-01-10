from __future__ import with_statement

from contextlib import contextmanager
import gevent
import gevent_zeromq
from gevent_selfpipe import selfpiped

from bson import BSON
from nose.tools import assert_equal
import zmq

from zrpc.concurrency import GeventCallback
from zrpc.server import Registry
from zrpc.multiserver import MultiServer


REGISTRY = Registry()

@REGISTRY.method
def add(x, y):
    return x + y


@contextmanager
def multiserver_and_client(address, registry, n_workers, context=None):
    context = context or zmq.Context.instance()

    try:
        cb = GeventCallback()
        ms = MultiServer(address, registry, context=context)
        ms_gl = cb.spawn(ms.run, args=(n_workers,),
                         kwargs={'callback': cb,
                                 'device': selfpiped(zmq.device)})

        cb.wait()
        client = context.socket(zmq.REQ)
        client.connect(address)

        try:
            yield client
        finally:
            client.close()
    finally:
        selfpiped(context.term)()


def test_server_responds_correctly():
    context = gevent_zeromq.zmq.Context()
    with multiserver_and_client('inproc://zrpc', REGISTRY, 4, context=context) as client:
        client.send(BSON.encode({
            "id": "abc",
            "method": "add",
            "params": [3, 4]}))
        assert_equal(BSON(client.recv()).decode(),
                     {"id": "abc", "result": 7, "error": None})
