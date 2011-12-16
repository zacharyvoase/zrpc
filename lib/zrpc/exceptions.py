class ZRPCError(Exception):
    """A generic error somewhere in the ZRPC error."""
    pass


class MissingMethod(Exception):
    """The requested method was not defined on the server."""
    pass
