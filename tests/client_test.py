import unittest

from ludibrio import Mock
from ludibrio.matcher import instance_of
from nose.tools import assert_raises
import zmq

from zrpc.client import Client, Error


def mock_context(request, response):
    with Mock() as context:
        context.__len__() >> 1
        socket = context.socket(zmq.REQ)
        socket.connect('inproc://zrpc')
        socket.send_json(request)
        socket.recv_json() >> response
    return context


def test_client_returns_result_on_success():
    context = mock_context(
        request={"id": instance_of(str), "method": "add", "params": [3, 4]},
        response={"id": "abc", "result": 7, "error": None})

    client = Client('inproc://zrpc', context=context)
    assert client.add(3, 4) == 7
    context.validate()


def test_client_raises_exception_on_failure():
    context = mock_context(
        request={"id": instance_of(str), "method": "add", "params": [3]},
        response={"id": "abc", "result": None,
                  "error": {"type": "exceptions.TypeError",
                            "message": "TypeError: add expected 2 arguments, got 1",
                            "args": ["add expected 2 arguments, got 1"]}})

    client = Client('inproc://zrpc', context=context)
    assert_raises(Error, client.add, 3)
    context.validate()


def test_dotted_names_resolve_to_dotted_methods():
    context = mock_context(
        request={"id": instance_of(str), "method": "math.add", "params": [3, 4]},
        response={"id": "abc", "result": 7, "error": None})

    client = Client('inproc://zrpc', context=context)
    assert client.math.add(3, 4) == 7
    context.validate()


class ClientErrorTest(unittest.TestCase):

    def setUp(self):
        self.exc = Error(
            request={"id": "abc", "method": "add", "params": [1]},
            response={"id": "abc", "result": None,
                      "error": {"type": "exceptions.TypeError",
                                "message": "TypeError: add expected 2 arguments, got 1",
                                "args": ["add expected 2 arguments, got 1"]}})

    def test_error_is_a_subclass_of_dynamically_created_classes(self):
        assert isinstance(self.exc, Error)
        assert isinstance(self.exc, Error.TypeError)
        assert isinstance(self.exc, Error['TypeError'])
        assert isinstance(self.exc, Error['exceptions.TypeError'])

    def test_error_stores_request_info(self):
        assert self.exc.id == "abc"
        assert self.exc.method == "add"
        assert self.exc.params == [1]

    def test_error_stores_exc_info(self):
        assert self.exc.type == "exceptions.TypeError"
        assert self.exc.message == "TypeError: add expected 2 arguments, got 1"
        assert self.exc.args == ["add expected 2 arguments, got 1"]
