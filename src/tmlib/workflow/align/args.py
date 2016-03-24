from ..args import VariableArgs


class AlignInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class MetaconfigInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.ref_cycle = self._ref_cycle_params['default']
        self.batch_size = self._batch_size_params['default']
        self.limit = self._limit_params['default']
        super(AlignInitArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {
            'batch_size', 'ref_cycle', 'ref_channel', 'limit',
        }

    @property
    def batch_size(self):
        '''
        Returns
        -------
        int
            number of image files that should be registered per job
            (default: ``5``)
        '''
        return self._batch_size

    @batch_size.setter
    def batch_size(self, value):
        if not isinstance(value, self._batch_size_params['type']):
            raise TypeError('Attribute "batch_size" must have type %s'
                            % self._batch_size_params['type'].__name__)
        self._batch_size = value

    @property
    def _batch_size_params(self):
        return {
            'type': int,
            'default': 5,
            'help': '''
                number of image files that should be registered per job
                (default: 5)
            '''
        }

    @property
    def ref_cycle(self):
        '''
        Returns
        -------
        int
            zero-based index of the reference cycle in the sequence of cycles
        '''
        return self._ref_cycle

    @ref_cycle.setter
    def ref_cycle(self, value):
        if not isinstance(value, self._ref_cycle_params['type']):
            raise TypeError('Attribute "ref_cycle" must have type %s'
                            % self._ref_cycle_params['type'].__name__)
        self._ref_cycle = value

    @property
    def _ref_cycle_params(self):
        return {
            'type': int,
            'default': 0,
            'help': '''
                zero-based index of the reference cycle (default: 0)
            '''
        }

    @property
    def ref_channel(self):
        '''
        Returns
        -------
        int
            name of the reference channel

        Note
        ----
        The `ref_channel` name must exist in all cycles.
        '''
        return self._ref_channel

    @ref_channel.setter
    def ref_channel(self, value):
        if not isinstance(value, self._ref_channel_params['type']):
            raise TypeError('Attribute "ref_channel" must have type %s'
                            % self._ref_channel_params['type'].__name__)
        self._ref_channel = value

    @property
    def _ref_channel_params(self):
        return {
            'type': str,
            'required': True,
            'help': '''
                name of the reference channel
            '''
        }

    @property
    def limit(self):
        '''
        Returns
        -------
        int
            shift limit, i.e. maximally tolerated shift value in pixels unit
            (default: ``300``)

        Warning
        -------
        If the calculated shift exceeds the `limit` the site will be omitted
        from further analysis.
        '''
        return self._limit

    @limit.setter
    def limit(self, value):
        if not isinstance(value, self._limit_params['type']):
            raise TypeError('Attribute "limit" must have type %s'
                            % self._limit_params['type'].__name__)
        self._limit = value

    @property
    def _limit_params(self):
        return {
            'type': int,
            'default': 300,
            'help': '''
                shift limit, i.e. maximally allowed shift in pixels
                (default: 300)
            '''
        }
