

# class addparams(object):

#     def __init__(self, default):
#         self.default = default
#         self._prepare_func(None)

#     def __call__(self, func):
#         func.default = self.default
#         self._prepare_func(func)
#         return self

#     def __get__(self, obj):
#         value = self.func(obj)
#         # obj.__dict__[self.__name__] = value
#         return value

#     def __set__(self, obj, value):
#         if value != self.default:
#             print 'wrong'
#         obj.__dict__[self.__name__] = value

#     def _prepare_func(self, func):
#         self.func = func
#         if func:
#             self.__doc__ = func.__doc__
#             self.__name__ = func.__name__
#             self.__module__ = func.__module__


def addparams(default):

    def wrap(f):
        # f.default = default

        @property
        def _wrap(default):
            f.default = default
            f()

        return _wrap

    return wrap



class Args(object):

    def __init__(self):
        pass

    @addparams(default='hello')
    def argument(self):
        return self._argument

    @argument.setter
    def argument(self, value):
        self._argument = value

    
class Args(object):

    @addparams(default='hello')
    def argument(self):
        return 'bla'
