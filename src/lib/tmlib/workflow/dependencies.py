from abc import ABCMeta


class WorkflowDependencies(object):

    '''Abstract base class for declaring workflow dependencies.

    They will be used by descriptor classes in
    :module:`tmlib.worklow.description`. To this end, derived classes need
    to be registered using the class decorator
    :function:`tmlib.workflow.registry.workflow`.
    '''

    __metaclass__ = ABCMeta
