import uuid

from bson import BSON
import zmq


class Error(Exception):

    _class_cache = {}

    class __metaclass__(type):

        def _get_error_cls(cls, error_type):
            generic_type = error_type.split('.')[-1]
            if generic_type not in cls._class_cache:
                cls._class_cache[generic_type] = type(
                    'Error', (cls,), {})
            if error_type not in cls._class_cache:
                cls._class_cache[error_type] = type(
                    'Error', (cls._class_cache[generic_type],), {})
            return cls._class_cache[error_type]

        # `Error.TypeError` => the cached error class.
        __getattr__ = _get_error_cls

        # `Error['exceptions.TypeError']` => the cached error class.
        __getitem__ = _get_error_cls

    def __new__(cls, request, response):
        return super(Error, cls).__new__(
            cls._get_error_cls(response['error']['type']),
            request, response)

    def __init__(self, request, response):
        self.request = request
        self.response = response

    def __repr__(self):
        return 'Error[%s]' % (self.type,)

    def __str__(self):
        return self.message

    @property
    def id(self):
        return self.request['id']

    @property
    def method(self):
        return self.request['method']

    @property
    def params(self):
        return self.request['params']

    @property
    def type(self):
        return self.response['error']['type']

    @property
    def message(self):
        return self.response['error']['message']

    @property
    def args(self):
        return self.response['error']['args']


class Client(object):

    def __init__(self, addr, context=None):
        self.context = context or zmq.Context.instance()
        self.addr = addr
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.addr)

    def __getattr__(self, method):
        return self[method]

    def __getitem__(self, method):
        return ClientMethod(self, method)

    def _process_response(self, request, response):
        if not response['error']:
            return response['result']
        raise Error(request, response)

    def __call__(self, method, *params):
        request = {"id": get_uuid(),
                   "method": method,
                   "params": params}
        self.socket.send(BSON.encode(request))
        return self._process_response(request,
                                      BSON(self.socket.recv()).decode())


class ClientMethod(object):

    def __init__(self, client, method):
        self.__client = client
        self.__method = method

    def __getattr__(self, attr):
        return self[attr]

    def __getitem__(self, item):
        return ClientMethod(self.__client, '%s.%s' % (self.__method, item))

    def __call__(self, *args, **kwargs):
        return self.__client(self.__method, *args, **kwargs)


def get_uuid():
    return str(uuid.uuid4()).replace('-', '')
