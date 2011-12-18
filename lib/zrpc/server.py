from __future__ import with_statement

from contextlib import closing, nested
from itertools import repeat
import traceback

import logbook
import simplejson
import zmq

from zrpc.registry import Registry


logger = logbook.Logger('zrpc.server')


class Server(object):

    """
    A ZRPC server.

    A :class:`Server` listens on a ``zmq.REP`` socket for incoming requests,
    performs the requested methods (using a :class:`Registry`) and returns the
    result. All communication is JSON-encoded.

    Usage is pretty simple:

        >>> server = Server('tcp://127.0.0.1:7341', registry)
        >>> server.run()

    You could even start a new thread/greenlet/process, using the server's
    `run()` method as the target. This library does not enforce or encourage
    any single concurrency model.

    .. py:attribute:: addr
        The address to bind or connect to as a ZeroMQ-style address. Examples
        include ``'tcp://*:7341'`` and ``'inproc://tasks'``.

    .. py:attribute:: registry
        A :class:`Registry` object holding the method definitions for this
        server.

    .. py:attribute:: connect
        A boolean indicating whether the server should bind or connect to its
        address. Default is ``False``, so the server will bind. Set to ``True``
        if you're using a broker-model :class:`LoadBalancer`, and specify the
        output address of that load balancer as this server's `addr`.

    .. py:attribute:: context
        A ``zmq.Context`` to use when creating sockets. Can be left unspecified
        and a new context will be created.
    """

    def __init__(self, addr, registry, connect=False, context=None):
        self.context = context or zmq.Context.instance()
        self.addr = addr
        self.connect = connect
        self.registry = registry

    def get_response(self, func, *args, **kwargs):

        """
        Run a Python function, returning the result in JSON-RPC form.

        The behaviour of this function is to capture either a successful return
        value or exception in the JSON-RPC form (a dictionary with `result` and
        `error` keys).
        """

        result, error = None, None
        try:
            result = func(*args, **kwargs)
        except Exception, exc:
            exc_type = "%s.%s" % (type(exc).__module__, type(exc).__name__)
            exc_message = traceback.format_exception_only(type(exc), exc)[-1].strip()
            error = {"type": exc_type,
                     "message": exc_message}
            try:
                simplejson.dumps(exc.args)
            except TypeError:
                pass
            else:
                error["args"] = exc.args

        return {'result': result, 'error': error}

    def process_message(self, message):

        """
        Process a single message.

        At the moment this just does some logging and dispatches to
        :meth:`get_response`, using the :attr:`registry`. You can override this
        in a subclass to customize the way messages are interpreted or methods
        are called.
        """

        if 'id' in message:
            logger.debug("Processing message {0}: {1!r}",
                         message['id'], message['method'])
        else:
            logger.debug("Processing method {0!r}", message['method'])

        response = self.get_response(self.registry,
                                     message['method'],
                                     *message['params'])
        if 'id' in message:
            response['id'] = message['id']
        return response

    def run(self, die_after=None, bind_callback=None):

        """
        Run the worker, optionally dying after a number of requests.

        :param int die_after:
            Die after processing a set number of messages (default: continue
            forever).

        :param bind_callback:
            A function/method which will be called with the socket once it has
            been successfully connected or bound. By using the ``put()`` method
            of a ``Queue.Queue`` here you can wait until the server is bound
            before beginning client initialization, for example.
        """

        socket = self.context.socket(zmq.REP)
        if self.connect:
            logger.debug("Replying to requests from {0!r}", self.addr)
            socket.connect(self.addr)
        else:
            logger.debug("Listening for requests on {0!r}", self.addr)
            socket.bind(self.addr)

        if bind_callback:
            bind_callback(socket)

        iterator = die_after and repeat(None, die_after) or repeat(None)
        with nested(logger.catch_exceptions(), closing(socket)):
            for _ in iterator:
                message = socket.recv_json()
                socket.send_json(self.process_message(message))
