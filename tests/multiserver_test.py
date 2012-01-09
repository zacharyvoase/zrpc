from __future__ import with_statement

from contextlib import contextmanager
import threading

from bson import BSON
from nose.tools import assert_equal
import zmq

from zrpc.concurrency import Callback
from zrpc.server import Registry
from zrpc.multiserver import MultiServer


REGISTRY = Registry()

@REGISTRY.method
def add(x, y):
    return x + y


@contextmanager
def multiserver_and_client(address, registry, n_workers):
    context = zmq.Context.instance()

    try:
        cb = Callback()
        ms = MultiServer(address, registry, context=context)
        ms_thread = cb.spawn(ms.run, args=(n_workers,),
                             kwargs={'callback': cb}, daemon=True)

        cb.wait()
        client = context.socket(zmq.REQ)
        client.connect(address)

        try:
            yield client
        finally:
            client.close()
    finally:
        context.term()


def test_server_responds_correctly():
    with multiserver_and_client('inproc://zrpc', REGISTRY, 4) as client:
        client.send(BSON.encode({
            "id": "abc",
            "method": "add",
            "params": [3, 4]}))
        assert_equal(BSON(client.recv()).decode(),
                     {"id": "abc", "result": 7, "error": None})
