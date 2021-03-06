
class BaseType(object):
    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self._get_items() == other._get_items())

    def __ne__(self, other):
        return not self == other

    def _get_items(self):
        return [(name, getattr(self, name)) for name in self._attrs_]

    def __hash__(self):
        return hash((self.__class__, tuple(self._get_items())))

    def prepare_backend_type(self, ffi):
        pass

    def finish_backend_type(self, ffi, *args):
        try:
            return ffi._cached_btypes[self]
        except KeyError:
            return self.new_backend_type(ffi, *args)

    def get_backend_type(self, ffi):
        return ffi._get_cached_btype(self)

    def verifier_declare(self, verifier, f):
        # nothing to see here
        pass

class VoidType(BaseType):
    _attrs_ = ()
    name = 'void'
    
    def new_backend_type(self, ffi):
        return ffi._backend.new_void_type()

    def __repr__(self):
        return '<void>'

void_type = VoidType()

class PrimitiveType(BaseType):
    _attrs_ = ('name',)

    def __init__(self, name):
        self.name = name

    def new_backend_type(self, ffi):
        return ffi._backend.new_primitive_type(self.name)

    def __repr__(self):
        return '<%s>' % (self.name,)

class FunctionType(BaseType):
    _attrs_ = ('args', 'result', 'ellipsis')

    def __init__(self, name, args, result, ellipsis):
        self.name = name # can be None in case it's an empty type
        self.args = args
        self.result = result
        self.ellipsis = ellipsis

    def __repr__(self):
        args = ', '.join([repr(x) for x in self.args])
        if self.ellipsis:
            return '<(%s, ...) -> %r>' % (args, self.result)
        return '<(%s) -> %r>' % (args, self.result)

    def prepare_backend_type(self, ffi):
        args = [ffi._get_cached_btype(self.result)]
        for tp in self.args:
            args.append(ffi._get_cached_btype(tp))
        return args

    def new_backend_type(self, ffi, result, *args):
        return ffi._backend.new_function_type(args, result, self.ellipsis)

    def verifier_declare(self, verifier, f):
        restype = self.result.name
        args = []
        for arg in self.args:
            args.append(arg.name)
        args = ', '.join(args)
        f.write('  %s(* res%d)(%s) = %s;\n' % (restype, verifier.rescount,
                                               args, self.name))
        verifier.rescount += 1

class PointerType(BaseType):
    _attrs_ = ('totype',)
    
    def __init__(self, totype):
        self.totype = totype

    def prepare_backend_type(self, ffi):
        return (ffi._get_cached_btype(self.totype),)

    def new_backend_type(self, ffi, BItem):
        return ffi._backend.new_pointer_type(BItem)

    def __repr__(self):
        return '<*%r>' % (self.totype,)

class ArrayType(BaseType):
    _attrs_ = ('item', 'length')

    def __init__(self, item, length):
        self.item = PointerType(item) # XXX why is this pointer?
        self.length = length

    def __repr__(self):
        if self.length is None:
            return '<%r[]>' % (self.item,)
        return '<%r[%s]>' % (self.item, self.length)

    def prepare_backend_type(self, ffi):
        return (ffi._get_cached_btype(self.item),)

    def new_backend_type(self, ffi, BItem):
        return ffi._backend.new_array_type(BItem, self.length)

class StructOrUnion(BaseType):
    _attrs_ = ('name',)
        
    def __init__(self, name, fldnames, fldtypes, fldbitsize):
        self.name = name
        self.fldnames = fldnames
        self.fldtypes = fldtypes
        self.fldbitsize = fldbitsize

    def __repr__(self):
        if self.fldnames is None:
            return '<struct %s>' % (self.name,)
        fldrepr = ', '.join(['%s: %r' % (name, tp) for name, tp in
                             zip(self.fldnames, self.fldtypes)])
        return '<struct %s {%s}>' % (self.name, fldrepr)

    def prepare_backend_type(self, ffi):
        BType = self.get_btype(ffi)
        ffi._cached_btypes[self] = BType
        args = [BType]
        for tp in self.fldtypes:
            args.append(ffi._get_cached_btype(tp))
        return args

    def finish_backend_type(self, ffi, BType, *fldtypes):
        ffi._backend.complete_struct_or_union(BType, self, fldtypes)
        return BType

class StructType(StructOrUnion):
    def get_btype(self, ffi):
        return ffi._backend.new_struct_type(self.name)

    def verifier_declare(self, verifier, f):
        verifier._write_printf(f, 'BEGIN struct %s size(%%ld)' % self.name,
                      'sizeof(struct %s)' % self.name)
        for decl in decl.decls:
            pass
            #_write_printf(f, 'FIELD ofs(%s) size(%s)')
        verifier._write_printf(f, 'END struct %s' % self.name)

class UnionType(StructOrUnion):
    def get_btype(self, ffi):
        return ffi._backend.new_union_type(self.name)
    
class EnumType(BaseType):
    _attrs_ = ('name',)

    def __init__(self, name, enumerators, enumvalues):
        self.name = name
        self.enumerators = enumerators
        self.enumvalues = enumvalues

    def new_backend_type(self, ffi):
        return ffi._backend.new_enum_type(self.name, self.enumerators,
                                          self.enumvalues)
