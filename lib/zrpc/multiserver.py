from contextlib import closing, nested
from Queue import Queue
import threading
import uuid

import logbook
import zmq

from zrpc.concurrency import Callback, DummyCallback
from zrpc.loadbal import LoadBalancer
from zrpc.server import Server


logger = logbook.Logger('zrpc.multiserver')


class MultiServer(object):

    """A multi-threaded ZMQ server."""

    def __init__(self, addr, registry, connect=False, context=None):
        self.context = context or zmq.Context.instance()
        self.addr = addr
        self.connect = connect
        self.registry = registry

    def run_device(self, callback=DummyCallback(), device=zmq.device):

        """
        Run the ZMQ queue device in a background thread.

        The return value of this function will be the address of the device's
        output socket (an `inproc://`-type address). In order to kill the
        background thread, you need to terminate the context the device is
        attached to.
        """

        output_addr = 'inproc://%s' % uuid.uuid4()
        loadbal = LoadBalancer(self.addr, output_addr, context=self.context)
        loadbal_thread = callback.spawn(loadbal.run,
                                        kwargs={'callback': callback,
                                                'device': device})
        return output_addr

    def run(self, n_workers, callback=DummyCallback(), device=zmq.device):
        loadbal_callback = type(callback)()
        loadbal_addr = self.run_device(callback=loadbal_callback,
                                       device=device)
        # We need the load balancer to be bound before continuing.
        loadbal_callback.wait()

        with callback.catch_exceptions():
            server = Server(loadbal_addr, self.registry, connect=True,
                            context=self.context)
            server_threads = []
            server_callbacks = []

            for i in xrange(n_workers):
                server_callback = type(callback)()
                server_thread = server_callback.spawn(
                    server.run, kwargs={'callback': server_callback})
                server_threads.append(server_thread)
                server_callbacks.append(server_callback)

            # Wait for all callbacks to complete before triggering ours.
            server_sockets = [server_callback.wait()
                            for server_callback in server_callbacks]

        callback.send(server_sockets)

        return loadbal_addr, server_threads
