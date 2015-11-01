from ..args import VariableArgs


class MetaextractInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class MetaextractInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        super(MetaextractInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return set()
