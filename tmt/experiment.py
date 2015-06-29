import re
import os
from os.path import isdir, join, basename
from natsort import natsorted
from tmt.util import regex_from_format_string
from tmt.project import Project


class Experiment(object):
    '''
    Utility class for an experiment.

    An experiment may represent a "project" itself or it may contain one or
    several subexperiments, each of them representing a "project".
    '''

    def __init__(self, experiment_dir, cfg):
        '''
        Initialize Experiment class.

        Parameters
        ----------
        experiment_dir: str
            absolute path to experiment folder
        cfg: Dict[str, str]
            configuration settings
        '''
        self.cfg = cfg
        self.experiment_dir = experiment_dir
        self.experiment_name = basename(experiment_dir)
        self._subexperiments = None
        self._project = None
        self._data_filename = None

    def is_valid_subexperiment(self, folder_name):
        '''
        Check whether a folder represents a valid subexperiment.

        Returns
        -------
        bool
        '''
        regexp = regex_from_format_string(
                        self.cfg['SUBEXPERIMENT_FOLDER_FORMAT'])
        return(re.match(regexp, folder_name)
               and isdir(join(self.experiment_dir, folder_name)))

    @property
    def subexperiments(self):
        '''
        Returns
        -------
        List[Subexperiment]

        Raises
        ------
        AttributeError
            when there are no subexperiments
        '''
        if self._subexperiments is None:
            experiment_subfolders = os.listdir(self.experiment_dir)
            experiment_subfolders = natsorted(experiment_subfolders)
            folders = [Subexperiment(join(self.experiment_dir, f), self.cfg)
                       for f in experiment_subfolders
                       if self.is_valid_subexperiment(f)]
            if not folders:
                raise AttributeError('Experiment "%s" does not contain any '
                                     'subexperiments' % self.experiment_name)
            self._subexperiments = folders
        return self._subexperiments

    @property
    def project(self):
        '''
        Returns
        -------
        Project
        '''
        if self._project is None:
            self._project = Project(self.experiment_dir, self.cfg)
        return self._project

    @property
    def data_filename(self):
        '''
        Returns
        -------
        str
            path to the HDF5 file holding the complete dataset
            (see `dafu` package)
        '''
        if self._data_filename is None:
            self._data_filename = self.cfg['DATA_FILE_LOCATION'].format(
                                        experiment_dir=self.experiment_dir,
                                        sep=os.path.sep)
        return self._data_filename


class Subexperiment(object):
    '''
    Utility class for a subexperiment.

    A subexperiment represents a child folder of an experiment folder.
    The class provides information on the subexperiment, such as its name,
    cycle number, and parent experiment's name.
    '''

    def __init__(self, subexperiment_dir, cfg):
        '''
        Initialize Subexperiment class.

        Parameters
        ----------
        subexperiment_dir: str
            path to the subexperiment folder
        cfg: Dict[str, str]
            configuration settings
        '''
        self.directory = subexperiment_dir
        self.name = basename(subexperiment_dir)
        self.cfg = cfg
        self._experiment = None
        self._cycle = None
        self._project = None

    @property
    def experiment(self):
        '''
        Returns
        -------
        str
            name of the corresponding parent experiment, determined from
            format string provided in configuration settings

        Raises
        ------
        ValueError
            when the experiment name cannot not be determined from format string
        '''
        if self._experiment is None:
            regexp = regex_from_format_string(
                            self.cfg['SUBEXPERIMENT_FOLDER_FORMAT'])
            m = re.search(regexp, self.name)
            if not m:
                raise ValueError('Can\'t determine experiment from '
                                 'subexperiment folder "%s" '
                                 'using provided format "%s".\n'
                                 'Check your configuration settings!'
                                 % (self.name,
                                    self.cfg['SUBEXPERIMENT_FOLDER_FORMAT']))
            self._experiment = m.group('experiment')
        return self._experiment

    @property
    def cycle(self):
        '''
        Returns
        -------
        int
            cycle number, determined from format string
            provided in configuration settings

        Raises
        ------
        ValueError
            when cycle number cannot not be determined from format string
        '''
        if self._cycle is None:
            regexp = regex_from_format_string(
                            self.cfg['SUBEXPERIMENT_FOLDER_FORMAT'])
            m = re.search(regexp, self.name)
            if not m:
                raise ValueError('Can\'t determine cycle from '
                                 'subexperiment folder "%s" '
                                 'using provided format "%s".\n'
                                 'Check your configuration settings!'
                                 % (self.name,
                                    self.cfg['SUBEXPERIMENT_FOLDER_FORMAT']))
            self._cycle = int(m.group('cycle'))
        return self._cycle

    @property
    def project(self):
        '''
        Returns
        -------
        Project
        '''
        if self._project is None:
            self._project = Project(self.directory, self.cfg)
        return self._project

    def __str__(self):
        return '%s - %s' % (self.experiment, self.cycle)

    def __unicode__(self):
        return self.__str__()
