from ..args import Args


class CorillaInitArgs(Args):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class CorillaInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        super(CorillaInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return set()
