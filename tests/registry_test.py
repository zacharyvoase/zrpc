import unittest

from zrpc.registry import Registry


class RegistryTest(unittest.TestCase):

    def test_registry_can_register_worker_methods(self):
        def func():
            return 123
        r = Registry()
        r.method(func)
        assert r['func'] is func

    def test_registry_can_register_worker_methods_with_explicit_names(self):
        def func():
            return 123
        r = Registry()
        r.method(func, name='some_method')
        assert r['some_method'] is func

    def test_registry_method_can_be_used_as_a_decorator(self):
        r = Registry()
        @r.method
        def func():
            return 123
        assert r['func'] is func

    def test_registry_method_decorator_accepts_explicit_names(self):
        r = Registry()
        @r.method(name='some_method')
        def func():
            return 123
        assert r['some_method'] is func

    def test_calling_registry_dispatches_to_method(self):
        r = Registry()
        r['method'] = lambda x: x + 12
        assert r('method', 24) == 36
