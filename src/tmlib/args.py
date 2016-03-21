import re
import json
from abc import ABCMeta
from abc import abstractproperty
import logging

logger = logging.getLogger(__name__)


class Args(object):

    '''
    Abstract base class for arguments of *TissueMAPS* steps. 
    '''

    __metaclass__ = ABCMeta

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class Args.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs

        Warning
        -------
        Only known arguments are stripped from `kwargs` and any
        unknown arguments are ignored.
        '''
        if kwargs:
            # for a in self._required_args:
            #     if a not in kwargs.keys():
            #         raise ValueError('Argument "%s" is required.' % a)
            for key, value in kwargs.iteritems():
                if not isinstance(key, basestring):
                    raise TypeError('"kwargs" keys must have type basestring')
                if isinstance(value, basestring):
                    value = str(value)
                if key in self._persistent_attrs:
                    logger.debug('set argument "%s"', key)
                    setattr(self, key, value)
                else:
                    logger.debug('argument "%s" is ignored', key)

    @abstractproperty
    def _persistent_attrs(self):
        # should return a set of strings
        pass

    def __iter__(self):
        for attr in dir(self):
            if attr.startswith('__') or attr.endswith('__'):
                continue
            if attr.startswith('_'):
                attr = re.search(r'_(.*)', attr).group(1)
            if attr in self._persistent_attrs:
                yield (attr, getattr(self, attr))

    def add_to_argparser(self, parser, ignore=set()):
        '''
        Add the attributes as arguments to `parser` using
        `add_argument() <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_.

        Parameters
        ----------
        parser: argparse.ArgumentParser
            parser or subparser object
        ignore: List[str]
            names of arguments that should not be added to the parser
        '''
        for attr in dir(self):
            if attr in self._persistent_attrs and attr not in ignore:
                if attr == 'variable_args':
                    continue
                params = '_%s_params' % attr
                if not hasattr(self, params):
                    raise AttributeError(
                            '"%s" object must have an "%s" attribute'
                            % (self.__class__.__name__, params))
                kwargs = dict(getattr(self, params))  # make a copy
                # There is no logic for dealing with a boolean "type" argument.
                # This is handled via the "action" argument.
                if kwargs['type'] == bool:
                    if kwargs['default']:
                        kwargs['action'] = 'store_false'
                    else:
                        kwargs['action'] = 'store_true'
                    del kwargs['type']
                # Arguments "experiment_dir" and "verbosity" get special
                # treatment because they are arguments of the main parser and
                # shared across all command line interfaces.
                if attr == 'key_file':
                    # Positional arguments cannot have "required" argument
                    del kwargs['required']
                    parser.add_argument(attr, **kwargs)
                elif attr == 'verbosity':
                    flags = ['--%s' % attr]
                    flags.append('-v')
                    kwargs['action'] = 'count'
                    # "type" argument is conflicting with "action" argument
                    del kwargs['type']
                    parser.add_argument(*flags, **kwargs)
                else:
                    flags = ['--%s' % attr]
                    parser.add_argument(*flags, **kwargs)

    def jsonify(self):
        '''
        Convert the attributes of the class into a JSON encoded list.

        Returns
        -------
        str
            JSON string that encodes for each argument a mapping with "name",
            "value", "help", "default", and "options" hyperparameters
        '''
        args = list()
        for attr in dir(self):
            if attr.startswith('_'):
                continue
            if attr in self._persistent_attrs:
                arg = dict()
                arg['name'] = attr
                arg['value'] = getattr(self, attr)
                params = dict(getattr(self, '_%s_params' % attr))
                if 'choices' in params:
                    # sets are not JSON serializable
                    params['choices'] = list(params['choices'])
                if params['type'] == bool:
                    params['choices'] = [True, False]
                del params['type']  # types are not JSON serializable
                if 'action' in params:
                    del params['action']
                if 'nargs' in params:
                    del params['nargs']
                # TODO: format value of type and nargs
                # The information could be used in the GUI to check format
                # the input accordingly (map to Javascript datatypes?)
                arg.update(params)
                args.append(arg)
        return json.dumps(args)


class GeneralArgs(Args):

    '''
    Class for general arguments that are shared between different steps;
    they correspond the main parser of command line interfaces.
    '''

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class GeneralArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.variable_args = VariableArgs()
        self.verbosity = self._verbosity_params['default']
        super(GeneralArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'key_file', 'verbosity'}

    @property
    def key_file(self):
        '''
        Returns
        -------
        str
            path to the key file
        '''
        return self._key_file

    @key_file.setter
    def key_file(self, value):
        if not isinstance(value, self._key_file_params['type']):
            raise TypeError('Attribute "backup" must have type %s.'
                            % self._key_file_params['type'].__name__)
        self._key_file = value

    @property
    def _key_file_params(self):
        return {
            'type': str,
            'required': True,
            'help': 'path to key file'
        }

    @property
    def verbosity(self):
        '''
        Returns
        -------
        int
            logging verbosity level

        See also
        --------
        :py:func:`tmlib.logging_utils.map_logging_verbosity`
        '''
        return self._verbosity

    @verbosity.setter
    def verbosity(self, value):
        if not isinstance(value, self._verbosity_params['type']):
            raise TypeError('Attribute "backup" must have type %s.'
                            % self._verbosity_params['type'].__name__)
        self._experiment_dir = value

    @property
    def _verbosity_params(self):
        return {
            'default': 0,
            'type': int,
            'help': 'increase logging verbosity'
        }

    @property
    def variable_args(self):
        '''
        Returns
        -------
        tmlib.args.VariableArgs
            additional step-specific arguments

        Note
        ----
        Each step (`tmlib` subpackage) must contain a module named "args",
        which must implement a step-specific subclass of
        :py:class:`tmlib.args.VariableArgs`.

        See also
        --------
        :py:class:`tmlib.cfg.WorkflowStepDescription`
        '''
        return self._variable_args

    @variable_args.setter
    def variable_args(self, value):
        if not(isinstance(value, VariableArgs) or value is None):
            raise TypeError(
                    'Attribute "variable_args" must have type '
                    'tmlib.args.VariableArgs')
        self._variable_args = value


class VariableArgs(Args):

    '''
    Class for variable, step-specific arguments;
    they correspond to the subparsers of command line interfaces.
    '''

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class VariableArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(VariableArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class InitArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class InitArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.backup = self._backup_params['default']
        self.keep_output = self._keep_output_params['default']
        super(InitArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'backup', 'keep_output'}

    @property
    def backup(self):
        '''
        Returns
        -------
        bool
            indicator that a backup of job descriptions and log output of a
            previous submission should be created
        '''
        return self._backup

    @backup.setter
    def backup(self, value):
        if not isinstance(value, self._backup_params['type']):
            raise TypeError('Attribute "backup" must have type %s.'
                            % self._backup_params['type'].__name__)
        self._backup = value

    @property
    def _backup_params(self):
        return {
            'default': False,
            'type': bool,
            'help': '''
                create a backup of the job descriptions and log output
                of a previous submission
            '''
        }

    @property
    def keep_output(self):
        '''
        Returns
        -------
        bool
            indicator that the output of a prior submission should be kept,
            i.e. not cleaned up
        '''
        return self._keep_output

    @keep_output.setter
    def keep_output(self, value):
        if not isinstance(value, self._keep_output_params['type']):
            raise TypeError('Attribute "keep_output" must have type %s.'
                            % self._keep_output_params['type'].__name__)
        self._keep_output = value

    @property
    def _keep_output_params(self):
        return {
            'default': False,
            'type': bool,
            'help': '''
                keep output of a prior submission, i.e. don't cleanup
            '''
        }


class SubmitArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class SubmitArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.interval = self._interval_params['default']
        self.depth = self._depth_params['default']
        self.duration = self._duration_params['default']
        self.memory = self._memory_params['default']
        self.cores = self._cores_params['default']
        self.phase = self._phase_params['default']
        self.jobs = self._jobs_params['default']
        self.backup = self._backup_params['default']
        super(SubmitArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {
            'interval', 'phase', 'jobs', 'depth',
            'memory', 'duration', 'cores',
            'backup'
        }

    @property
    def jobs(self):
        '''
        Returns
        -------
        List[int]
            ids of *run* jobs that should be submitted (default: ``None``)

        Note
        ----
        Can only be set if value of attribute `phase` is ``"run"``.
        '''
        return self._jobs

    @jobs.setter
    def jobs(self, value):
        if not(isinstance(value, list) or value is None):
            raise TypeError('Attribute "jobs" must have type list')
        if value is None:
            self._jobs = value
            return
        if any([not isinstance(e, self._jobs_params['type']) for e in value]):
            raise TypeError(
                    'Elements of attribute "jobs" must have type %s.'
                    % self._jobs_params['type'].__name__)
        self._jobs = value

    @property
    def _jobs_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'help': '''
                one-based indices of jobs that should be submitted
                (requires argument "phase" to be set to "run")
            '''
        }

    @property
    def phase(self):
        '''
        Returns
        -------
        List[int]
            phase for which jobs should be submitted
            (options: ``"run"`` or ``"collect"``; default: ``None``)
        '''
        return self._phase

    @phase.setter
    def phase(self, value):
        if not(isinstance(value, self._phase_params['type']) or value is None):
            raise TypeError('Attribute "phase" must have type %s'
                            % self._phase_params['type'].__name__)
        self._phase = value

    @property
    def _phase_params(self):
        return {
            'type': str,
            'default': None,
            'choices': {'run', 'collect'},
            'help': '''
                phase for which jobs should be submitted
            '''
        }

    @property
    def interval(self):
        '''
        Returns
        -------
        int
            monitoring interval in seconds (default: ``1``)
        '''
        return self._interval

    @interval.setter
    def interval(self, value):
        if not(isinstance(value, self._interval_params['type']) or
               value is None):
            raise TypeError('Attribute "interval" must have type %s'
                            % self._interval_params['type'].__name__)
        self._interval = value

    @property
    def _interval_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                monitoring interval in seconds (default: 1)
            '''
        }

    @property
    def depth(self):
        '''
        Returns
        -------
        int
            monitoring recursion depth, i.e. how detailed status information of
            subtasks should be monitored during the processing of the jobs
            (default: ``1``)
        '''
        return self._depth

    @depth.setter
    def depth(self, value):
        if not isinstance(value, self._depth_params['type']):
            raise TypeError('Attribute "depth" must have type %s'
                            % self._depth_params['type'].__name__)
        self._depth = value

    @property
    def _depth_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                recursion depth for subtask monitoring (default: 1)
            '''
        }

    @property
    def duration(self):
        '''
        Returns
        -------
        str
            time that should be allocated for each job in HH:MM:SS
            (default: ``"02:00:00"``)
        '''
        return self._duration

    @duration.setter
    def duration(self, value):
        if not isinstance(value, self._duration_params['type']):
            raise TypeError('Attribute "duration" must have type %s'
                            % self._duration_params['type'].__name__)
        match = re.search(r'(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2})', value)
        results = match.groupdict()
        if any([r is None for r in results.values()]):
            raise ValueError(
                    'Attribute "duration" must have the format "HH:MM:SS"')
        self._duration = value

    @property
    def _duration_params(self):
        return {
            'type': str,
            'default': '02:00:00',
            'help': '''
                time that should be allocated for each job in HH:MM:SS
                (default: 02:00:00)
            '''
        }

    @property
    def memory(self):
        '''
        Returns
        -------
        int
            amount of memory that should be allocated for each job in GB
            (default: ``4``)
        '''
        return self._memory

    @memory.setter
    def memory(self, value):
        if not isinstance(value, self._memory_params['type']):
            raise TypeError('Attribute "memory" must have type %s'
                            % self._memory_params['type'].__name__)
        self._memory = value

    @property
    def _memory_params(self):
        return {
            'type': int,
            'default': 4,
            'help': '''
                amount of memory that should be allocated for each job in GB
            '''
        }

    @property
    def cores(self):
        '''
        Returns
        -------
        int
            number of CPUs that should be allocated for each job
            (default: ``1``)
        '''
        return self._cores

    @cores.setter
    def cores(self, value):
        if not isinstance(value, self._cores_params['type']):
            raise TypeError('Attribute "cores" must have type %s'
                            % self._cores_params['type'].__name__)
        self._cores = value

    @property
    def _cores_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                number of CPUs that should be allocated for each job
                (default: 1)
            '''
        }

    @property
    def backup(self):
        '''
        Returns
        -------
        bool
            indicator that the session of a previous submission should be
            backed up (default: ``False``)
        '''
        return self._backup

    @backup.setter
    def backup(self, value):
        if not isinstance(value, self._backup_params['type']):
            raise TypeError('Attribute "backup" must have type %s.'
                            % self._backup_params['type'].__name__)
        self._backup = value

    @property
    def _backup_params(self):
        return {
            'default': False,
            'type': bool,
            'help': '''
                backup the session of a previous submission
            '''
        }


class ResubmitArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class SubmitArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.interval = self._interval_params['default']
        self.depth = self._depth_params['default']
        self.duration = self._duration_params['default']
        self.memory = self._memory_params['default']
        self.cores = self._cores_params['default']
        self.phase = self._phase_params['default']
        self.jobs = self._jobs_params['default']
        super(ResubmitArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {
            'interval', 'phase', 'jobs', 'depth',
            'memory', 'duration', 'cores',
            'backup',
        }

    @property
    def jobs(self):
        '''
        Returns
        -------
        List[int]
            ids of *run* jobs that should be resubmitted (default: ``None``)

        Note
        ----
        Can only be set if value of attribute `phase` is ``"run"``.
        '''
        return self._jobs

    @jobs.setter
    def jobs(self, value):
        if not(isinstance(value, list) or value is None):
            raise TypeError('Attribute "jobs" must have type list')
        if value is None:
            self._jobs = value
            return
        if any([not isinstance(e, self._jobs_params['type'].__name__) for e in value]):
            raise TypeError(
                    'Elements of attribute "jobs" must have type %s.'
                    % self._jobs_params['type'].__name__)
        self._jobs = value

    @property
    def _jobs_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'help': '''
                one-based indices of jobs that should be resubmitted
                (requires argument "phase" to be set to "run")
            '''
        }

    @property
    def phase(self):
        '''
        Returns
        -------
        List[int]
            phase for which jobs should be resubmitted
            (options: ``"run"`` or ``"collect"``; default: ``None``)
        '''
        return self._phase

    @phase.setter
    def phase(self, value):
        if not(isinstance(value, self._phase_params['type']) or value is None):
            raise TypeError('Attribute "phase" must have type %s'
                            % self._phase_params['type'].__name__)
        self._phase = value

    @property
    def _phase_params(self):
        return {
            'type': str,
            'default': None,
            'required': True,
            'choices': {'run', 'collect'},
            'help': '''
                phase for which jobs should be resubmitted
            '''
        }

    @property
    def interval(self):
        '''
        Returns
        -------
        int
            monitoring interval in seconds (default: ``1``)
        '''
        return self._interval

    @interval.setter
    def interval(self, value):
        if not(isinstance(value, self._interval_params['type']) or
               value is None):
            raise TypeError('Attribute "interval" must have type %s'
                            % self._interval_params['type'].__name__)
        self._interval = value

    @property
    def _interval_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                monitoring interval in seconds (default: 1)
            '''
        }

    @property
    def depth(self):
        '''
        Returns
        -------
        int
            monitoring recursion depth, i.e. how detailed status information of
            subtasks should be monitored during the processing of the jobs
            (default: ``1``)
        '''
        return self._depth

    @depth.setter
    def depth(self, value):
        if not isinstance(value, self._depth_params['type']):
            raise TypeError('Attribute "depth" must have type %s'
                            % self._depth_params['type'].__name__)
        self._depth = value

    @property
    def _depth_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                recursion depth for subtask monitoring (default: 1)
            '''
        }

    @property
    def duration(self):
        '''
        Returns
        -------
        str
            time that should be allocated for each job in HH:MM:SS
            (default: ``"02:00:00"``)
        '''
        return self._duration

    @duration.setter
    def duration(self, value):
        if not isinstance(value, self._duration_params['type']):
            raise TypeError('Attribute "duration" must have type %s'
                            % self._duration_params['type'].__name__)
        self._duration = value

    @property
    def _duration_params(self):
        return {
            'type': str,
            'default': '02:00:00',
            'help': '''
                time that should be allocated for each job in HH:MM:SS
                (default: 02:00:00)
            '''
        }

    @property
    def memory(self):
        '''
        Returns
        -------
        int
            amount of memory that should be allocated for each job in GB
            (default: ``4``)
        '''
        return self._memory

    @memory.setter
    def memory(self, value):
        if not isinstance(value, self._memory_params['type']):
            raise TypeError('Attribute "memory" must have type %s'
                            % self._memory_params['type'].__name__)
        self._memory = value

    @property
    def _memory_params(self):
        return {
            'type': int,
            'default': 4,
            'help': '''
                amount of memory that should be allocated for each job in GB
            '''
        }

    @property
    def cores(self):
        '''
        Returns
        -------
        int
            number of CPUs that should be allocated for each job
            (default: ``1``)
        '''
        return self._cores

    @cores.setter
    def cores(self, value):
        if not isinstance(value, self._cores_params['type']):
            raise TypeError('Attribute "cores" must have type %s'
                            % self._cores_params['type'].__name__)
        self._cores = value

    @property
    def _cores_params(self):
        return {
            'type': int,
            'default': 1,
            'help': '''
                number of CPUs that should be allocated for each job
                (default: 1)
            '''
        }


class CollectArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class CollectArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(CollectArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class CleanupArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class CleanupArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(CleanupArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class RunArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class RunArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(RunArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'job'}

    @property
    def job(self):
        '''
        Returns
        -------
        int
            one-based job index
        '''
        return self._job

    @job.setter
    def job(self, value):
        if not isinstance(value, self._job_params['type']):
            raise TypeError('Attribute "job" must have type %s'
                            % self._job_params['type'].__name__)
        self._job = value

    @property
    def _job_params(self):
        return {
            'type': int,
            'required': True,
            'help': '''
                one-based job index
            '''
        }


class LogArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class LogArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.job = self._job_params['default']
        super(LogArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'phase', 'job'}

    @property
    def phase(self):
        '''
        Returns
        -------
        List[int]
            phase for which job log should be displayed
            (options: ``"run"`` or ``"collect"``)
        '''
        return self._phase

    @phase.setter
    def phase(self, value):
        if not(isinstance(value, self._phase_params['type']) or value is None):
            raise TypeError('Attribute "phase" must have type %s'
                            % self._phase_params['type'].__name__)
        self._phase = value

    @property
    def _phase_params(self):
        return {
            'type': str,
            'required': True,
            'choices': {'run', 'collect'},
            'help': '''
                phase for which job log should be displayed
            '''
        }

    @property
    def job(self):
        '''
        Returns
        -------
        int
            one-based job index
        '''
        return self._job

    @job.setter
    def job(self, value):
        if not(isinstance(value, self._job_params['type']) or value is None):
            raise TypeError('Attribute "job" must have type %s'
                            % self._job_params['type'].__name__)
        self._job = value

    @property
    def _job_params(self):
        return {
            'type': int,
            'default': None,
            'help': '''
                one-based index of *run* job
                (requires argument "phase" to be set to "run")
            '''
        }


class InfoArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class InfoArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.job = self._job_params['default']
        super(InfoArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'phase', 'job'}

    @property
    def phase(self):
        '''
        Returns
        -------
        List[int]
            phase for which job description should be displayed
            (options: ``"run"`` or ``"collect"``)
        '''
        return self._phase

    @phase.setter
    def phase(self, value):
        if not(isinstance(value, self._phase_params['type']) or value is None):
            raise TypeError('Attribute "phase" must have type %s'
                            % self._phase_params['type'].__name__)
        self._phase = value

    @property
    def _phase_params(self):
        return {
            'type': str,
            'required': True,
            'choices': {'run', 'collect'},
            'help': '''
                phase for which job description should be displayed
            '''
        }

    @property
    def job(self):
        '''
        Returns
        -------
        int
            one-based job index
        '''
        return self._job

    @job.setter
    def job(self, value):
        if not(isinstance(value, self._job_params['type']) or value is None):
            raise TypeError('Attribute "job" must have type %s'
                            % self._job_params['type'].__name__)
        self._job = value

    @property
    def _job_params(self):
        return {
            'type': int,
            'default': None,
            'help': '''
                one-based index of *run* job
                (requires argument "phase" to be set to "run")
            '''
        }


class ApplyArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class ApplyArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.plates = self._plates_params['default']
        self.wells = self._wells_params['default']
        self.channels = self._channels_params['default']
        self.zplanes = self._zplanes_params['default']
        self.tpoints = self._tpoints_params['default']
        self.sites = self._sites_params['default']
        super(ApplyArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {
            'plates', 'wells', 'channels', 'tpoints', 'zplanes', 'sites',
            'output_dir'
        }

    @property
    def output_dir(self):
        '''
        Returns
        -------
        str
            path to the output directory
        '''
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value):
        if not isinstance(value, self._output_dir_params['type']):
            raise TypeError('Attribute "output_dir" must have type %s',
                            self._output_dir_params['type'].__name__)
        self._output_dir = str(value)

    @property
    def _output_dir_params(self):
        return {
            'type': str,
            'required': True,
            'help': '''
                path to the output directory
            '''
        }

    @property
    def plates(self):
        '''
        Returns
        -------
        str
            plate indices
        '''
        return self._plates

    @plates.setter
    def plates(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "plates" must have type list')
            if not(all([
                        isinstance(v, self._plates_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "plates" must have type %s'
                        % self._plates_params['type'].__name__)
        self._plates = value

    @property
    def _plates_params(self):
        return {
            'type': int,
            'default': None,
            'nargs': '+',
            'metavar': 'P',
            'help': '''
                plate indices
            '''
        }

    @property
    def wells(self):
        '''
        Returns
        -------
        str
            wells names
        '''
        return self._wells

    @wells.setter
    def wells(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "wells" must have type list')
            if not(all([
                        isinstance(v, self._wells_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "wells" must have type %s'
                        % self._wells_params['type'].__name__)
        self._wells = value

    @property
    def _wells_params(self):
        return {
            'type': str,
            'nargs': '+',
            'default': None,
            'metavar': 'W',
            'help': '''
                well names
            '''
        }

    @property
    def channels(self):
        '''
        Returns
        -------
        str
            channel indices
        '''
        return self._channels

    @channels.setter
    def channels(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "channels" must have type list')
            if not(all([
                        isinstance(v, self._channels_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "channels" must have type %s'
                        % self._channels_params['type'].__name__)
        self._channels = value

    @property
    def _channels_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'metavar': 'C',
            'help': '''
                channel indices
            '''
        }

    @property
    def zplanes(self):
        '''
        Returns
        -------
        str
            z-plane indices
        '''
        return self._zplanes

    @zplanes.setter
    def zplanes(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "zplanes" must have type list')
            if not(all([
                        isinstance(v, self._zplanes_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "zplanes" must have type %s'
                        % self._zplanes_params['type'].__name__)
        self._zplanes = value

    @property
    def _zplanes_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'metavar': 'Z',
            'help': '''
                z-plane indices
            '''
        }

    @property
    def tpoints(self):
        '''
        Returns
        -------
        str
            time point indices
        '''
        return self._tpoints

    @tpoints.setter
    def tpoints(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "tpoints" must have type list')
            if not(all([
                        isinstance(v, self._tpoints_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "tpoints" must have type %s'
                        % self._tpoints_params['type'].__name__)
        self._tpoints = value

    @property
    def _tpoints_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'metavar': 'T',
            'help': '''
                time point indices
            '''
        }

    @property
    def sites(self):
        '''
        Returns
        -------
        str
            acquisition site indices
        '''
        return self._sites

    @sites.setter
    def sites(self, value):
        if value is not None:
            if not(isinstance(value, list)):
                raise TypeError('Attribute "sites" must have type list')
            if not(all([
                        isinstance(v, self._sites_params['type'].__name__)
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "sites" must have type %s'
                        % self._sites_params['type'].__name__)
        self._sites = value

    @property
    def _sites_params(self):
        return {
            'type': int,
            'nargs': '+',
            'default': None,
            'metavar': 'S',
            'help': '''
                acquisition site indices
            '''
        }

# NOTE: The following argument classes are specific to the jterator program.
# However, they have to be defined here, since they get dynamically loaded
# from this module.


class CreateArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class CreateArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(CreateArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class RemoveArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class RemoveArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(RemoveArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class CheckArgs(GeneralArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class CheckArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(CheckArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return set()


class ResumeArgs(SubmitArgs):

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class ResumeArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        super(ResumeArgs, self).__init__(**kwargs)

    @property
    def _persistent_attrs(self):
        return {'interval', 'depth'}
