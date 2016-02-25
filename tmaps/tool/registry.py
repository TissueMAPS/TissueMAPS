# Location to save all registered tools
_tools = {}


def get_tool(tool_id):
    """Return a new instance of the Tool with type `tool_id`"""
    if tool_id in _tools:
        cls = _tools[tool_id]
        return cls
    else:
        available_tool_ids = ', '.join(_tools.keys())
        raise Exception(
            'No tool with id %s registered! Available tools: %s'
            % (tool_id, available_tool_ids))


def register_tool(tool_id):
    """
    Class decorator needed to register a Tool class.

    This decorator is to be used as follows:

    @register_tool('my_new_tool')
    class MyNewTool(object):

        # Required method
        def process_request(payload):
            return {
                some_key: some_value
            }
    """
    def cls_decorator(tool_cls):
        if tool_id in _tools:
            msg = (
                'WARNING: There is already a tool with id "%s". '
                'The class under this id: "%s"' % str(tool_id, _tools[tool_id]))
            print msg
        else:
            required_methods = ['process_request']
            for m in required_methods:
                # Check that the registered class has the required methods.
                if not m in tool_cls.__dict__:
                    print 'The class %s needs to provide the method %s' \
                        % (str(tool_cls), m)
                else:
                    # The method is present in the class,
                    # throw an error if its return type is wrong.
                    # For this we need to wrap the original method with another
                    # function

                    # This outer wrap function is necessary that orig method
                    # is in a new scope. Otherwise both wrapped functions
                    # would call the same `orig_method`.
                    def wrap():
                        orig_method = getattr(tool_cls, m)

                        def wrapped_method(self, *args, **kwargs):
                            ret = orig_method(self, *args, **kwargs)
                            # if not (isinstance(ret, GenericResponse) or isinstance(ret, LayerModResponse)):
                            #     msg = (
                            #         'The method "%s" of class "%s" needs to return '
                            #         'an instance of a supported response class, but it returned an '
                            #         'instance of class "%s")' % (m, str(tool_cls), type(ret)))
                            #     raise Exception(msg)
                            return ret

                        return wrapped_method
                    setattr(tool_cls, m, wrap())

                _tools[tool_id] = tool_cls

    return cls_decorator
