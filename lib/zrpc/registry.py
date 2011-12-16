class Registry(dict):

    """
    Interface for registering ZRPC methods.

    Begin by creating a registry and registering methods on it:

        >>> registry = Registry()
        >>> @registry.method
        ... def add_two_numbers(value1, value2):
        ...     return value1 + value2
    
    You can then dispatch to methods by calling the registry itself:

        >>> registry('add_two_numbers', 3, 4)
        7
    """

    def method(self, *args, **kwargs):
        def register_method(method):
            name = kwargs.get('name', method.__name__)
            self[name] = method
            return method

        if args:
            return register_method(*args)
        return register_method

    def __call__(self, method_name, *args, **kwargs):
        return self[method_name](*args, **kwargs)
