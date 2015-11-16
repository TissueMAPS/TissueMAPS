from ..args import Args


class TmapsSubmitArgs(Args):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class TmapsSubmitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.backup = False
        super(TmapsSubmitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'backup'}

    @property
    def backup(self):
        '''
        Returns
        -------
        bool
            indicator that an existing session should be overwritten
            (default: ``False``)
        '''
        return self._backup

    @backup.setter
    def backup(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "backup" must have type bool.')
        self._backup = value

    @property
    def _backup_params(self):
        return {
            'action': 'store_true',
            'help': '''
                backup an existing session
            '''
        }


class TmapsResumeArgs(Args):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class TmapsResumeArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        super(TmapsResumeArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set('stage', 'step')

    @property
    def _persistent_attrs(self):
        return {'stage', 'step'}

    @property
    def stage(self):
        '''
        Returns
        -------
        str
            name of the stage from where workflow should be started
            (default: ``None``)
        '''
        return self._stage

    @stage.setter
    def stage(self, value):
        if not(isinstance(value, self._stage_params['type']) or value is None):
            raise TypeError('Attribute "stage" must have type %s'
                            % self._stage_params['type'])
        self._stage = value

    @property
    def _stage_params(self):
        return {
            'type': str,
            'help': '''
                name of the stage from where workflow should be started
            '''
        }

    @property
    def step(self):
        '''
        Returns
        -------
        str
            name of the step from where workflow should be started
            (default: ``None``)
        '''
        return self._step

    @step.setter
    def step(self, value):
        if not(isinstance(value, self._step_params['type']) or value is None):
            raise TypeError('Attribute "step" must have type %s'
                            % self._step_params['type'])
        self._step = value

    @property
    def _step_params(self):
        return {
            'type': str,
            'help': '''
                name of the step from where workflow should be started
            '''
        }
