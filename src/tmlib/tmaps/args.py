from ..args import VariableArgs


class TmapsSubmitArgs(VariableArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class TmapsSubmitArgs.

        Parameters
        ----------
        **kwargs: dict
            arguments as key-value pairs
        '''
        self.stage = self._stage_params['default']
        self.step = self._step_params['default']
        super(TmapsSubmitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'stage', 'step', 'backup'}

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
        if (not(isinstance(value, self._stage_params['type']) or
                value is None)):
            raise TypeError('Attribute "stage" must have type %s'
                            % self._stage_params['type'].__name__)
        self._stage = value

    @property
    def _stage_params(self):
        return {
            'type': str,
            'default': None,
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
        if (not(isinstance(value, self._step_params['type']) or
                value is None)):
            raise TypeError('Attribute "step" must have type %s'
                            % self._step_params['type'].__name__)
        self._step = value

    @property
    def _step_params(self):
        return {
            'type': str,
            'default': None,
            'help': '''
                name of the step from where workflow should be started
            '''
        }
