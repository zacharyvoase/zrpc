"""
Common exceptions throughout the ZRPC server.

Note that :class:`zrpc.client.Error` doesn't live here; this module houses
server-specific exceptions.
"""

class ZRPCError(Exception):
    """A generic error somewhere in the ZRPC server."""
    pass


class MissingMethod(Exception):
    """The requested method was not defined on the server."""
    pass
