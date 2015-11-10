from ..args import VariableArgs


class JteratorInitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class JteratorInitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        super(JteratorInitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return set()


class JteratorRunArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class JteratorRunArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.plot = False
        super(JteratorRunArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'plot'}

    @property
    def plot(self):
        '''
        Returns
        -------
        bool
            indicator that modules should generate plots (default: ``False``)
        '''
        return self._headless

    @plot.setter
    def plot(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "plot" must have type bool.')
        self._headless = value

    @property
    def _plot_params(self):
        return {
            'action': 'store_true',
            'help': '''
                turn on plotting mode
            '''

        }


class JteratorCreateArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class JteratorCreateArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.repo_dir = self._repo_dir_params['default']
        self.skel_dir = self._skel_dir_params['default']
        super(JteratorCreateArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'repo_dir', 'skel_dir'}

    @property
    def repo_dir(self):
        '''
        Returns
        -------
        str
            path to repository directory where module files are located
        '''
        return self._repo_dir

    @repo_dir.setter
    def repo_dir(self, value):
        if not(isinstance(value, self._repo_dir_params['type'])
               or value is None):
            raise TypeError('Attribute "repo_dir" must have type %s'
                            % self._repo_dir_params['type'])
        self._repo_dir = value

    @property
    def _repo_dir_params(self):
        return {
            'type': basestring,
            'default': None,
            'help': '''
                path to repository directory where module files are located
            '''
        }

    @property
    def skel_dir(self):
        '''
        Returns
        -------
        str
            path to a directory that represents a project skeleton 
        '''
        return self._skel_dir

    @skel_dir.setter
    def skel_dir(self, value):
        if not(isinstance(value, self._skel_dir_params['type'])
               or value is None):
            raise TypeError('Attribute "skel_dir" must have type %s'
                            % self._skel_dir_params['type'])
        self._skel_dir = value

    @property
    def _skel_dir_params(self):
        return {
            'type': basestring,
            'default': None,
            'help': '''
                path to repository directory where module files are located
            '''
        }


