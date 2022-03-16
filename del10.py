# class BaseClass(object):
#     def __init__(self, classtype):
#         self._type = classtype
#
#
# def ClassFactory(name, argnames, BaseClass=BaseClass):
#     def __init__(self, **kwargs):
#         for key, value in kwargs.items():
#             # here, the argnames variable is the one passed to the
#             # ClassFactory call
#             if key not in argnames:
#                 raise TypeError("Argument %s not valid for %s"
#                                 % (key, self.__class__.__name__))
#             setattr(self, key, value)
#         BaseClass.__init__(self, name[:-len("Class")])
#     newclass = type(name, (BaseClass,),{"__init__": __init__})
#     return newclass
#
#
# class OperationMeta(ClassFactory):
#     def __call__(cls, operation_type, *args, **kwargs):
#         operation_cls = cls.registry.get(operation_type)
#         if operation_cls is None:
#             raise TypeError('Invalid operation {0}'.format(operation_type))
#         return super(OperationMeta, operation_cls).__call__(*args, **kwargs)
#
#     create = __call__


class Operation(object):
    # __metaclass__ = OperationMeta

    def __init__(self, name):
        self.name = name

    def execute(self):
        print(self.name)


class OnOperation(Operation):
    _factory_id = 'on'

    def __init__(self):
        super(OnOperation, self).__init__('On operation')


class OffOperation(Operation):
    _factory_id = 'off'

    def __init__(self):
        super(OffOperation, self).__init__('Off operation')


class ShutdownOperation(Operation):
    _factory_id = 'shutdown'

    def __init__(self):
        super(ShutdownOperation, self).__init__('Shutdown operation')

# from op_factory import Operation
print (Operation.registry)
print (Operation.registry['on'])

# factory = {}
#
#
# class Smith(object):
#     def __init__(self, a, b):
#         self.a = a
#         self.b = b
# factory['Smith'] = Smith
#
#
# class Jones(object):
#     def __init__(self, c, d):
#         self.c = c
#         self.d = d
#
# factory['Jones'] = Jones
#
# s = factory['Smith'](1, 2)
# j = factory['Jones'](3, 4)