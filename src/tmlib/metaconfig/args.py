from ..args import VariableArgs
from ..formats import Formats


class MetaconfigInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class MetaconfigInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.file_format = self._file_format_params['default']
        self.keep_z_stacks = self._keep_z_stacks_params['default']
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
            'file_format', 'keep_z_stacks', 'regex', 'stitch_layout',
            'stitch_major_axis', 'n_vertical', 'n_horizontal'
        }

    @property
    def file_format(self):
        '''
        Returns
        -------
        str
            microscope-specific file format for which a custom
            reader and handler is available (default: ``"default"``)
        '''
        return self._file_format

    @file_format.setter
    def file_format(self, value):
        if not isinstance(value, self._file_format_params['type']):
            raise TypeError('Attribute "file_format" must have type %s'
                            % self._file_format_params['type'].__name__)
        options = set(self._file_format_params['choices'])
        options.add(self._file_format_params['default'])
        if value not in options:
            raise ValueError('Attribute of "file_format" must be "%s"'
                             % '" or "'.join(options))
        self._file_format = value

    @property
    def _file_format_params(self):
        return {
            'type': str,
            'choices': Formats.SUPPORT_FOR_ADDITIONAL_FILES,
            'default': 'default',
            'help': '''
                microscope-specific file format for which a custom
                reader and handler is available (default: "default")
            '''
        }

    @property
    def keep_z_stacks(self):
        '''
        Returns
        -------
        bool
            if individual focal planes should be kept,
            i.e. no intensity projection performed (default: ``False``)
        '''
        return self._keep_z_stacks

    @keep_z_stacks.setter
    def keep_z_stacks(self, value):
        if not isinstance(value, self._keep_z_stacks_params['type']):
            raise TypeError('Attribute "keep_z_stacks" must have type %s.'
                            % self._keep_z_stacks_params['type'].__name__)
        self._keep_z_stacks = value

    @property
    def _keep_z_stacks_params(self):
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
