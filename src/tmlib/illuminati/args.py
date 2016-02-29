from ..args import VariableArgs


class IlluminatiInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class IlluminatiInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.batch_size = self._batch_size_params['default']
        self.align = self._align_params['default']
        self.illumcorr = self._illumcorr_params['default']
        self.clip = self._clip_params['default']
        self.clip_value = self._clip_value_params['default']
        super(IlluminatiInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {
            'batch_size', 'align', 'illumcorr', 'clip', 'clip_value'
        }

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

    @property
    def align(self):
        '''
        Returns
        -------
        bool
            indicates whether images should be aligned between cycles
        '''
        return self._align

    @align.setter
    def align(self, value):
        if not isinstance(value, self._align_params['type']):
            raise TypeError('Attribute "align" must have type %s.'
                            % self._align_params['type'].__name__)
        self._align = value

    @property
    def _align_params(self):
        return {
            'type': bool,
            'default': False,
            'help': '''
                align images between cycles
            '''
        }

    @property
    def illumcorr(self):
        '''
        Returns
        -------
        bool
            indicates whether images should be corrected for illumination
            artifacts
        '''
        return self._illumcorr

    @illumcorr.setter
    def illumcorr(self, value):
        if not isinstance(value, self._illumcorr_params['type']):
            raise TypeError('Attribute "illumcorr" must have type %s.'
                            % self._illumcorr_params['type'].__name__)
        self._illumcorr = value

    @property
    def _illumcorr_params(self):
        return {
            'type': bool,
            'default': False,
            'help': '''
                correct images for illumination artifacts
            '''
        }

    @property
    def clip(self):
        '''
        Returns
        -------
        bool
            indicates whether pixel values above a certain level
            should be clipped
        '''
        return self._clip

    @clip.setter
    def clip(self, value):
        if not isinstance(value, self._clip_params['type']):
            raise TypeError('Attribute "clip" must have type %s.'
                            % self._clip_params['type'].__name__)
        self._clip = value

    @property
    def _clip_params(self):
        return {
            'type': bool,
            'default': False,
            'help': '''
                clip pixel values above a certain level,
                i.e. rescale images between min value and clip level
            '''
        }

    @property
    def clip_values(self):
        '''
        Returns
        -------
        int
            pixel value that should be used as clip level (default: ``None``)
        '''
        return self._clip_values

    @clip_values.setter
    def clip_values(self, value):
        if not isinstance(value, self._clip_value_params['type']):
            raise TypeError('Attribute "clip_values" must have type %s.'
                            % self._clip_value_params['type'].__name__)
        self._clip_values = value

    @property
    def _clip_value_params(self):
        return {
            'type': int,
            'default': None,
            'help': '''
                pixel value that should be used as clip level
            '''
        }
