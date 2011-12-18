# ZRPC

ZRPC is a library for building and using simple [ZeroMQ][]-based [JSON-RPC][]
1.0 servers.

  [zeromq]: http://zeromq.org/
  [json-rpc]: http://json-rpc.org/


## Server Example

    from zrpc.server import Registry, Server

    # Create a registry and define some methods.
    registry = Registry()

    @registry.method
    def add(*values):
        return sum(values)

    @registry.method
    def factorial(n):
        return reduce(lambda x, y: x * y, xrange(1, n + 1))

    # Create and run a server using the registry.
    server = Server('tcp://*:5000', registry)
    server.run()


## Client Example

    from zrpc.client import Client

    c = Client('tcp://127.0.0.1:5000')
    assert c.add(3, 4) == 7
    assert c.factorial(20) == 2432902008176640000


## Load Balancer Example

    from zrpc.loadbal import LoadBalancer

    # The 'proxy' model -- the list of downstream servers is fixed.
    lb = LoadBalancer('tcp://127.0.0.1:5010', ('tcp://127.0.0.1:5000',))
    lb.run()

    # The 'broker' model -- downstream servers can come and go, but they need
    # to specify `connect=True` with an address of 'tcp://127.0.0.1:5005' to
    # connect to the output port of the balancer.
    lb = LoadBalancer('tcp://127.0.0.1:5010', 'tcp://127.0.0.1:5005')
    lb.run()
