
class WorkflowDescription(object):

    '''
    Description of a TissueMAPS processing workflow.

    A workflow consists of *stages*, which themselves are made up of *steps*.

    Each *step* is a collection of individual tasks, which can be processed
    in parallel on a computer cluster.

    The workflow is described by a mapping of key-value pairs::

        mapping = {
            "workflow":
                "stages": [
                    {
                        "name": "",
                        "steps": [
                            {
                                "name": "",
                                "args": {}
                            },
                            ...
                        ]
                    },
                    ...
                ]
        }

    A WorkflowDescription can be constructed from a dictionary and converted
    back into a dictionary::

        >>>obj = WorkflowDescription(mapping)
        >>>dict(obj)

    See also
    --------
    :mod:`tmlib.tmaps.descriptions.WorkflowStageDescription`
    :mod:`tmlib.tmaps.descriptions.WorkflowStepDescription`
    '''

    def __init__(self, description):
        '''
        Initialize an instance of class WorkflowDescription.

        Parameters
        ----------
        description: dict, optional
            description of a workflow

        Returns
        -------
        tmlib.tmaps.description.WorkflowDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        '''
        if not isinstance(description, dict):
            raise TypeError('Argument "description" must have type dict.')
        if 'stages' not in description:
            raise KeyError('Argument "description" must have key "stages".')
        self._stages = [
            WorkflowStageDescription(s) for s in description['stages']
        ]

    @property
    def stages(self):
        '''
        Returns
        -------
        List[tmlib.tmaps.description.WorkflowStageDescription]
            description of each in the workflow
        '''
        return self._stages

    @stages.setter
    def stages(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "stages" must have type list')
        if not all([isinstance(v, WorkflowStageDescription) for v in value]):
            raise TypeError(
                'Elements of "steps" must have type WorkflowStageDescription')
        self._workflow = value

    def __iter__(self):
        yield ('stages', dict(getattr(self, 'stages')))


class WorkflowStageDescription(object):

    '''
    Description of a TissueMAPS workflow stage.
    '''

    def __init__(self, description=None):
        '''
        Initialize an instance of class WorkflowStageDescription.

        Parameters
        ----------
        description: dict, optional
            description of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStageDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have the keys "name" and "steps"
        '''
        if not isinstance(description, dict):
            raise TypeError('Argument "description" must have type dict.')
        if not('name' in description and 'steps' in description):
            raise KeyError(
                'Argument "description" must have keys "name" and "steps".')
        self._name = description['name']
        self._steps = [
            WorkflowStepDescription(s) for s in description['steps']
        ]

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the stage

        Note
        ----
        Must correspond to a name of a `tmlib` command line program
        (subpackage).
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        self._name = str(value)

    @property
    def steps(self):
        '''
        Returns
        -------
        List[tmlib.tmaps.description.WorkflowStepDescription]
            description of each step that is part of the workflow stage
        '''
        return self._steps

    @steps.setter
    def steps(self, value):
        if not isinstance(value, list):
            raise TypeError('Attribute "steps" must have type list')
        if not all([isinstance(v, WorkflowStepDescription) for v in value]):
            raise TypeError(
                'Elements of "steps" must have type WorkflowStepDescription')
        self._workflow = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('steps', dict(getattr(self, 'steps')))


class WorkflowStepDescription(object):

    '''
    Description of a step as part of a TissueMAPS workflow stage.
    '''

    def __init__(self, description=None):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        description: dict, optional
            description of a step of a workflow stage

        Returns
        -------
        tmlib.tmaps.description.WorkflowStepDescription

        Raises
        ------
        TypeError
            when `description` doesn't have type dict
        KeyError
            when `description` doesn't have the keys "name" and "args"
        '''
        self._name = description['name']
        self._args = description['args']

    @property
    def name(self):
        '''
        Returns
        -------
        str
            name of the step

        Note
        ----
        Must correspond to a name of a `tmlib` command line program
        (subpackage).
        '''
        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
            raise TypeError('Attribute "name" must have type basestring')
        self._name = str(value)

    @property
    def args(self):
        '''
        Returns
        -------
        dict
            arguments required by the step (arguments that can be parsed
            to the "init" method of the corresponding *cli* class)

        Note
        ----
        Default values defined by the corresponding *init* subparser will
        be used in case an optional argument is not provided.

        See also
        --------
        `tmlib.cli`_
        '''
        return self._args

    @args.setter
    def args(self, value):
        if not isinstance(value, dict) or value is not None:
            raise TypeError('Attribute "args" must have type dict')
        self._args = value

    def __iter__(self):
        yield ('name', getattr(self, 'name'))
        yield ('args', getattr(self, 'args'))
