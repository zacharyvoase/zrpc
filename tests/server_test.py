from __future__ import with_statement

from contextlib import contextmanager
from Queue import Queue
import threading

from bson import BSON
from nose.tools import assert_equal
import zmq

from zrpc.concurrency import Callback
from zrpc.server import Server
from zrpc.registry import Registry


REGISTRY = Registry()

@REGISTRY.method
def add(x, y):
    return x + y


@REGISTRY.method
def raises_error():
    raise Exception("some error occurred")


@contextmanager
def server(addr, registry, connect=False, context=None):
    context = context or zmq.Context.instance()

    # Set up a server, tell it to run in a separate thread, and pass in a
    # callback so that we can wait for the server to be bound before connecting
    # our client. This avoids an issue we were having with inproc:// transport,
    # wherein if the client connected before the server had bound, it would
    # raise an error.
    callback = Callback()
    server = Server(addr, registry, connect=connect, context=context)
    server_thread = threading.Thread(
        target=server.run,
        kwargs=dict(callback=callback))
    server_thread.daemon = True
    server_thread.start()
    server_socket = callback.wait()

    try:
        yield
    finally:
        context.term()


@contextmanager
def get_client(addr, context=None):
    context = context or zmq.Context.instance()
    client = context.socket(zmq.REQ)
    client.connect(addr)
    try:
        yield client
    finally:
        client.close()


@contextmanager
def server_and_client(addr, registry, connect=False, context=None):
    context = context or zmq.Context.instance()

    with server(addr, registry, connect=connect, context=context):
        with get_client(addr, context=context) as client:
            yield client


def test_server_responds_correctly():
    with server_and_client('inproc://zrpc', REGISTRY) as client:
        client.send(BSON.encode({
            "id": "abc",
            "method": "add",
            "params": [3, 4]}))
        assert_equal(BSON(client.recv()).decode(),
                     {"id": "abc", "result": 7, "error": None})


def test_missing_method_returns_an_error():
    with server_and_client('inproc://zrpc', REGISTRY) as client:
        client.send(BSON.encode({
            "id": "abc",
            "method": "doesnotexist",
            "params": [3, 4]}))
        assert_equal(BSON(client.recv()).decode(),
                     {"id": "abc",
                      "result": None,
                      "error": {
                          "type": "zrpc.exceptions.MissingMethod",
                          "args": ["doesnotexist"],
                          "message": "MissingMethod: doesnotexist"
                      }})


def test_errors_raised_in_method_are_returned():
    with server_and_client('inproc://zrpc', REGISTRY) as client:
        client.send(BSON.encode({
            "id": "abc",
            "method": "raises_error",
            "params": []}))
        assert_equal(BSON(client.recv()).decode(),
                     {"id": "abc",
                      "result": None,
                      "error": {
                          "type": "exceptions.Exception",
                          "args": ["some error occurred"],
                          "message": "Exception: some error occurred"
                      }})
