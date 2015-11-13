import re
from abc import ABCMeta
from abc import abstractproperty
import logging

logger = logging.getLogger(__name__)


class Args(object):

    '''
    Abstract base class with attributes for arguments of *TissueMAPS* steps,
    i.e. the programs defined in *tmlib* subpackages. 
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
            for a in self._required_args:
                if a not in kwargs.keys():
                    raise ValueError('Argument "%s" is required.' % a)
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
    def _required_args(self):
        # should return a set of strings
        pass

    @abstractproperty
    def _persistent_attrs(self):
        # should return a set of strings
        pass

    def __iter__(self):
        for attr in vars(self):
            if attr.startswith('_'):
                attr = re.search(r'_(.*)', attr).group(1)
            if attr in self._persistent_attrs:
                yield (attr, getattr(self, attr))

    def add_to_argparser(self, parser):
        '''
        Add the attributes as arguments to `parser` using
        `add_argument() <https://docs.python.org/3/library/argparse.html#argparse.ArgumentParser.add_argument>`_.

        Parameters
        ----------
        parser: argparse.ArgumentParser
            parser or subparser object
        '''
        for attr in dir(self):
            if attr in self._persistent_attrs:
                if attr == 'variable_args':
                    continue
                flag = '--%s' % attr
                params = '_%s_params' % attr
                if not hasattr(self, params):
                    raise AttributeError(
                            '"%s" object must have an "%s" attribute'
                            % (self.__class__.__name__, params))
                kwargs = getattr(self, params)
                parser.add_argument(*[flag], **kwargs)


class GeneralArgs(Args):

    '''
    Class for arguments that are shared between different programs.
    '''

    def __init__(self, **kwargs):
        '''
        Initialize an instance of class GeneralArgs.

        Parameters
        ----------
        **kwargs: dict, optional
            arguments as key-value pairs
        '''
        self.variable_args = None
        super(GeneralArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return set()

    @property
    def variable_args(self):
        '''
        Returns
        -------
        tmlib.args.Args
            additional program-specific arguments

        Note
        ----
        Each program (`tmlib` subpackage) must contain a module named "args",
        which must implement a program-specific subclass of `Args`.

        See also
        --------
        :py:class:`tmlib.cfg.WorkflowStepDescription`
        '''
        return self._variable_args

    @variable_args.setter
    def variable_args(self, value):
        if not(isinstance(value, Args) or value is None):
            raise TypeError(
                    'Attribute "variable_args" must have type tmlib.args.Args')
        self._variable_args = value


class VariableArgs(Args):

    '''
    Class for variable, program-specific arguments.
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
    def _required_args(self):
        return set()

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
        self.backup = False
        self.display = False
        super(InitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {
            'display', 'backup', 'variable_args'
        }

    @property
    def display(self):
        '''
        Returns
        -------
        bool
            indicator that job descriptions should only be displayed
            and not written to files

        Warning
        -------
        This argument must not be set within workflows, since it will cause
        the program to exit without creating persistent job descriptions. 
        '''
        return self._display

    @display.setter
    def display(self, value):
        if not isinstance(value, bool):
            raise TypeError('Attribute "display" must have type bool.')
        self._display = value

    @property
    def _display_params(self):
        return {
            'action': 'store_true',
            'help': '''
                display job descriptions, i.e. pretty print descriptions
                to standard output without writing them to files
            '''
        }

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
        if not isinstance(value, bool):
            raise TypeError('Attribute "backup" must have type bool.')
        self._backup = value

    @property
    def _backup_params(self):
        return {
            'action': 'store_true',
            'help': '''
                create a backup of the job descriptions and log output
                of a previous submission
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
        self.virtualenv = self._virtualenv_params['default']
        self.interval = self._interval_params['default']
        self.depth = self._depth_params['default']
        super(SubmitArgs, self).__init__(**kwargs)

    @property
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return {'virtualenv', 'interval', 'depth', 'memory', 'duration'}

    @property
    def virtualenv(self):
        '''
        Returns
        -------
        str
            name of a virtual environment that needs to be activated
            (default: ``None``)
        '''
        return self._virtualenv

    @virtualenv.setter
    def virtualenv(self, value):
        if not(isinstance(value, self._virtualenv_params['type'])
               or value is None):
            raise TypeError('Attribute "virtualenv" must have type %s'
                            % self._virtualenv_params['type'])
        self._virtualenv = value

    @property
    def _virtualenv_params(self):
        return {
            'type': str,
            'default': None,
            'help': '''
                name of a virtual environment that needs to be activated
            '''
        }

    @property
    def interval(self):
        '''
        Returns
        -------
        int
            monitoring interval in seconds (default: ``5``)
        '''
        return self._interval

    @interval.setter
    def interval(self, value):
        if not(isinstance(value, self._interval_params['type'])
               or value is None):
            raise TypeError('Attribute "interval" must have type %s'
                            % self._interval_params['type'])
        self._interval = value

    @property
    def _interval_params(self):
        return {
            'type': int,
            'default': 5,
            'help': '''
                monitoring interval in seconds (default: 5)
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
                            % self._depth_params['type'])
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
        if not(isinstance(value, self._duration_params['type']) or value is None):
            raise TypeError('Attribute "duration" must have type %s'
                            % self._duration_params['type'])
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
            (default: ``2``)
        '''
        return self._memory

    @memory.setter
    def memory(self, value):
        if not(isinstance(value, self._memory_params['type']) or value is None):
            raise TypeError('Attribute "memory" must have type %s'
                            % self._memory_params['type'])
        self._memory = value

    @property
    def _memory_params(self):
        return {
            'type': int,
            'default': 2,
            'help': '''
                amount of memory that should be allocated for each job in GB
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
    def _required_args(self):
        return set()

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
    def _required_args(self):
        return set()

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
    def _required_args(self):
        return {'job'}

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
                            % self._job_params['type'])
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
    def _required_args(self):
        return {'output_dir'}

    @property
    def _persistent_attrs(self):
        return {
            'plates', 'wells', 'channels', 'tpoints', 'zplanes', 'sites'
        }

    @property
    def plates(self):
        '''
        Returns
        -------
        str
            plate names
        '''
        return self._plates

    @plates.setter
    def plates(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise TypeError('Attribute "plates" must have type list')
            if not(all([
                        isinstance(v, self._plates_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "plates" must have type %s'
                        % self._plates_params['type'])
        self._plates = value

    @property
    def _plates_params(self):
        return {
            'type': str,
            'default': None,
            'nargs': '+',
            'metavar': 'P',
            'help': '''
                plate names
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
                        isinstance(v, self._wells_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "wells" must have type %s'
                        % self._wells_params['type'])
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
                raise TypeError('Attribute "plates" must have type list')
            if not(all([
                        isinstance(v, self._plates_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "plates" must have type %s'
                        % self._plates_params['type'])
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
                        isinstance(v, self._zplanes_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "zplanes" must have type %s'
                        % self._zplanes_params['type'])
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
                        isinstance(v, self._tpoints_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "tpoints" must have type %s'
                        % self._tpoints_params['type'])
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
                        isinstance(v, self._sites_params['type'])
                        for v in value
                    ])):
                raise TypeError(
                        'Elements of attribute "sites" must have type %s'
                        % self._sites_params['type'])
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
    def _required_args(self):
        return set()

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
    def _required_args(self):
        return set()

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
    def _required_args(self):
        return set()

    @property
    def _persistent_attrs(self):
        return set()
