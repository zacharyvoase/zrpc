from contextlib import contextmanager
import threading

from nose.tools import assert_equal
import zmq

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
def server_and_client(addr, registry, die_after=None, timeout=1):
    context = zmq.Context()

    # The following is a little complicated; we set up a server, tell it to run
    # in a separate thread, and pass in a bind_callback so that we can wait for
    # the server to be bound before connecting our client. This avoids an issue
    # we were having with inproc:// transport, wherein if the client connected
    # before the server had bound, it would raise an error.
    server_bind = threading.Event()
    server = Server(addr, registry, context=context)
    server_thread = threading.Thread(
        target=server.run,
        kwargs=dict(die_after=die_after, bind_callback=server_bind.set))
    server_thread.start()

    client = context.socket(zmq.REQ)
    server_bind.wait()
    client.connect(addr)
    try:
        yield client
    finally:
        client.close()
        server_thread.join(timeout=timeout)


def test_server_responds_correctly():
    with server_and_client('inproc://tasks', REGISTRY, die_after=1) as client:
        client.send_json({
            "id": "abc",
            "method": "add",
            "params": [3, 4]})
        assert_equal(client.recv_json(),
                     {"id": "abc", "result": 7, "error": None})


def test_missing_method_returns_an_error():
    with server_and_client('inproc://tasks', REGISTRY, die_after=1) as client:
        client.send_json({
            "id": "abc",
            "method": "doesnotexist",
            "params": [3, 4]})
        assert_equal(client.recv_json(), {"id": "abc",
                                      "result": None,
                                      "error": {
                                          "type": "zrpc.exceptions.MissingMethod",
                                          "args": ["doesnotexist"],
                                          "message": "MissingMethod: doesnotexist"
                                      }})


def test_errors_raised_in_method_are_returned():
    with server_and_client('inproc://tasks', REGISTRY, die_after=1) as client:
        client.send_json({
            "id": "abc",
            "method": "raises_error",
            "params": []})
        assert_equal(client.recv_json(), {"id": "abc",
                                      "result": None,
                                      "error": {
                                          "type": "exceptions.Exception",
                                          "args": ["some error occurred"],
                                          "message": "Exception: some error occurred"
                                      }})
