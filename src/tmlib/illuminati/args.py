from ..args import Args


class IlluminatiInitArgs(Args):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class IlluminatiInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.align = False
        self.illumcorr = False
        self.clip = False
        self.clip_value = self._clip_value_params['default']
        self.clip_percentile = self._clip_percentile_params['default']
        super(IlluminatiInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {
            'align', 'illumcorr', 'clip', 'clip_value', 'clip_percentile'
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
        if not isinstance(value, bool):
            raise TypeError('Attribute "align" must have type bool.')
        self._align = value

    @property
    def _align_params(self):
        return {
            'action': 'store_true',
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
        if not isinstance(value, bool):
            raise TypeError('Attribute "illumcorr" must have type bool.')
        self._illumcorr = value

    @property
    def _illumcorr_params(self):
        return {
            'action': 'store_true',
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
        if not isinstance(value, bool):
            raise TypeError('Attribute "clip" must have type bool.')
        self._clip = value

    @property
    def _clip_params(self):
        return {
            'action': 'store_true',
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
                            % self._clip_value_params['type'])
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

    @property
    def clip_percentile(self):
        '''
        Returns
        -------
        float
            percentage of pixel values below clip level (default: ``99.9``)
        '''
        return self._clip_percentile

    @clip_percentile.setter
    def clip_percentile(self, value):
        if not isinstance(value, self._clip_percentile_params['type']):
            raise TypeError('Attribute "clip_percentile" must have type %s.'
                            % self._clip_percentile_params['type'])
        self._clip_percentile = value

    @property
    def _clip_percentile_params(self):
        return {
            'type': float,
            'default': 99.9,
            'help': '''
                percentage of pixel values below clip level
            '''
        }
