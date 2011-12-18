from __future__ import with_statement

from contextlib import contextmanager
from Queue import Queue
import threading

import zmq

from zrpc.loadbal import LoadBalancer


@contextmanager
def temporary_context():
    context = zmq.Context.instance()
    try:
        yield context
    finally:
        context.term()


@contextmanager
def run_loadbal(input, output, context=None):
    context = context or zmq.Context.instance()

    # Set up a callback so we can be notified when the device connects/binds
    # its input and output sockets. This resolves issues with attempting to
    # connect to `inproc:` sockets before they've been bound at the other end.
    queue = Queue()
    callback = lambda *args: queue.put(args)

    # Run the load balancer device in a separate thread. This will die once
    # all its sockets are closed and the context terminated.
    loadbal = LoadBalancer(input, output, context=context)
    loadbal_thread = threading.Thread(target=loadbal.run,
                                      kwargs={'setup_callback': callback})
    loadbal_thread.daemon = True
    loadbal_thread.start()

    in_sock, out_sock = queue.get()
    client = context.socket(zmq.REQ)
    client.connect(input)

    try:
        yield client
    finally:
        client.close()
        in_sock.close()
        out_sock.close()


@contextmanager
def run_worker(bind=None, connect=None, context=None):
    context = context or zmq.Context.instance()
    worker = context.socket(zmq.REP)
    if connect:
        worker.connect(connect)
    elif bind is None:
        raise ValueError("Must specify either `bind` or `connect`")
    else:
        worker.bind(bind)

    try:
        yield worker
    finally:
        worker.close()


def test_proxy_forwards_requests_to_specified_backends():
    with temporary_context():
        with run_worker(bind='inproc://worker0') as worker:
            with run_loadbal('inproc://zrpc', ('inproc://worker0',)) as client:
                request = {"id": "abc", "method": "add", "params": [3, 4]}
                response = {"id": "abc", "error": None, "result": 7}

                client.send_json(request)
                assert worker.recv_json() == request
                worker.send_json(response)
                assert client.recv_json() == response


def test_broker_forwards_requests_to_any_connected_backend():
    with temporary_context():
        with run_loadbal('inproc://zrpc-in', 'inproc://zrpc-out') as client:
            with run_worker(connect='inproc://zrpc-out') as worker:
                request = {"id": "abc", "method": "add", "params": [3, 4]}
                response = {"id": "abc", "error": None, "result": 7}

                client.send_json(request)
                assert worker.recv_json() == request
                worker.send_json(response)
                assert client.recv_json() == response
