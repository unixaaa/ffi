import py
from ffi import FFI

class FakeBackend(object):

    def nonstandard_integer_types(self):
        return {}

    def sizeof_type(self, name):
        return 1

    def load_library(self, path):
        return "fake library"

    def new_primitive_type(self, name):
        return FakePrimitiveType(name)

class FakePrimitiveType(object):

    def __init__(self, cdecl):
        self.cdecl = cdecl


def test_typeof():
    ffi = FFI(backend=FakeBackend())
    clong = ffi.typeof("signed long int")
    assert isinstance(clong, FakePrimitiveType)
    assert clong.cdecl == 'long'
