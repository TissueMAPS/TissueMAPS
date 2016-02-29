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
        self.batch_size = self._batch_size_params['default']
        super(MetaextractInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'batch_size'}

    @property
    def batch_size(self):
        '''
        Returns
        -------
        int
            number of image files that should be processed per job
            (default: ``10``)
        '''
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value):
        if not(isinstance(value, self._batch_size_params['type'])):
            raise TypeError('Attribute "batch_size" must have type %s'
                            % self._batch_size_params['type'].__name__)
        self._batch_size = value

    @property
    def _batch_size_params(self):
        return {
            'type': int,
            'default': 10,
            'help': '''
                number of image files that should be processed per job
                (default: 10)
            '''
        }
