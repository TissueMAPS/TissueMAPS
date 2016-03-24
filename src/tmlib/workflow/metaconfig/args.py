from tmlib.workflow.args import VariableArgs


class MetaconfigInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class MetaconfigInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.keep_zplanes = self._keep_zplanes_params['default']
        self.regex = self._regex_params['default']
        self.stitch_layout = self._stitch_layout_params['default']
        self.stitch_major_axis = self._stitch_major_axis_params['default']
        self.n_horizontal = self._n_horizontal_params['default']
        self.n_vertical = self._n_vertical_params['default']
        super(MetaconfigInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {
            'keep_zplanes', 'regex', 'stitch_layout',
            'stitch_major_axis', 'n_vertical', 'n_horizontal'
        }

    @property
    def keep_zplanes(self):
        '''
        Returns
        -------
        bool
            if individual focal planes should be kept,
            i.e. no intensity projection performed (default: ``False``)
        '''
        return self._keep_zplanes

    @keep_zplanes.setter
    def keep_zplanes(self, value):
        if not isinstance(value, self._keep_zplanes_params['type']):
            raise TypeError('Attribute "keep_zplanes" must have type %s.'
                            % self._keep_zplanes_params['type'].__name__)
        self._keep_zplanes = value

    @property
    def _keep_zplanes_params(self):
        return {
            'type': bool,
            'default': False,
            'help': '''
                keep individual focal planes,
                i.e. don't perform maximum intensity projection
            '''
        }

    @property
    def regex(self):
        '''
        Returns
        -------
        str
            named regular expression that defines group names
            "(?P<name>...)" for retrieval of metadata from image filenames
            (default: ``None``)
        '''
        return self._regex

    @regex.setter
    def regex(self, value):
        if not(isinstance(value, self._regex_params['type']) or
               value is None):
            raise TypeError('Attribute "regex" must have type %s'
                            % self._regex_params['type'].__name__)
        self._regex = value

    @property
    def _regex_params(self):
        return {
            'type': str,
            'default': None,
            'metavar': 'expression',
            'help': '''
                named regular expression that defines group names
                "(?P<name>...)" for retrieval of metadata from image filenames
            '''
        }

    @property
    def stitch_layout(self):
        '''
        Returns
        -------
        str
            layout of the stitched mosaic image, i.e. the order in which
            images are arrayed on the grid (default: ``zigzag_horizontal``)
        '''
        return self._stitch_layout

    @stitch_layout.setter
    def stitch_layout(self, value):
        if not isinstance(value, self._stitch_layout_params['type']):
            raise TypeError('Attribute "stitch_layout" must have type %s'
                            % self._stitch_layout_params['type'].__name__)
        options = self._stitch_layout_params['choices']
        if value not in options:
            raise ValueError('Attribute of "stitch_layout" must be "%s"'
                             % '" or "'.join(options))
        self._stitch_layout = value

    @property
    def _stitch_layout_params(self):
        return {
            'type': str,
            'default': 'zigzag_horizontal',
            'choices': {
                'horizontal', 'zigzag_horizontal',
                'vertical', 'zigzag_vertical'
            },
            'help': '''
                layout of the stitched mosaic image, i.e. the order in which
                images are arrayed on the grid (default: "zigzag_horizontal")
            '''
        }

    @property
    def stitch_major_axis(self):
        '''
        Returns
        -------
        str
            longer axis of the stitched mosaic image
            (default: ``vertical``)
        '''
        return self._stitch_major_axis

    @stitch_major_axis.setter
    def stitch_major_axis(self, value):
        if not isinstance(value, self._stitch_major_axis_params['type']):
            raise TypeError('Attribute "stitch_major_axis" must have type %s'
                            % self._stitch_major_axis_params['type'].__name__)
        options = self._stitch_major_axis_params['choices']
        if value not in options:
            raise ValueError('Attribute of "stitch_major_axis" must be "%s"'
                             % '" or "'.join(options))
        self._stitch_major_axis = value

    @property
    def _stitch_major_axis_params(self):
        return {
            'type': str,
            'default': 'vertical',
            'choices': {'vertical', 'horizontal'},
            'help': '''
                longer axis of the stitched mosaic image (default: "vertical")
            '''
        }

    @property
    def n_vertical(self):
        '''
        Returns
        -------
        int
            number of images along the vertical axis of each stitched mosaic
            (default: ``None``)
        '''
        return self._n_vertical

    @n_vertical.setter
    def n_vertical(self, value):
        if not(isinstance(value, self._n_vertical_params['type']) or
               value is None):
            raise TypeError('Attribute "n_vertical" must have type %s'
                            % self._n_vertical_params['type'].__name__)
        self._n_vertical = value

    @property
    def _n_vertical_params(self):
        return {
            'type': int,
            'default': None,
            'metavar': 'N_ROWS',
            'help': '''
                number of images along the vertical axis of each
                stitched mosaic
            '''
        }

    @property
    def n_horizontal(self):
        '''
        Returns
        -------
        int
            number of images along the horizontal axis of each stitched mosaic
            (default: ``None``)
        '''
        return self._n_horizontal

    @n_horizontal.setter
    def n_horizontal(self, value):
        if not(isinstance(value, self._n_horizontal_params['type']) or
               value is None):
            raise TypeError('Attribute "n_horizontal" must have type %s'
                            % self._n_horizontal_params['type'].__name__)
        self._n_horizontal = value

    @property
    def _n_horizontal_params(self):
        return {
            'type': int,
            'default': None,
            'metavar': 'N_COLUMNS',
            'help': '''
                number of images along the horizontal axis of each
                stitched mosaic
            '''
        }
