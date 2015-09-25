import os
import logging
import importlib
from cached_property import cached_property
from gc3libs.workflow import SequentialTaskCollection
from ..cluster import BasicClusterRoutines
from .. import utils

logger = logging.getLogger(__name__)


class ClusterWorkflow(BasicClusterRoutines):

    '''
    Class for building a workflow, i.e. a GC3Pie SequentialTaskCollection.

    For more information on the task collection, see
    `GCPie docs <http://gc3pie.readthedocs.org/en/latest/programmers/api/gc3libs/workflow.html?highlight=sequentialtaskcollection#gc3libs.workflow.SequentialTaskCollection>`_
    '''

    def __init__(self, experiment, no_shared_network, virtualenv):
        '''
        Initialize an instance of class ClusterWorkflow.

        Parameters
        ----------
        experiment: Experiment
            experiment object that holds information about the content of the
            experiment directory

        Returns
        -------
        ClusterWorkflow

        Note
        ----
        Creates an empty *task* list, which can be further extended
        and ultimately submitted to a cluster for processing.

        Warning
        -------
        If `no_shared_network` is set to ``True`` all files will be copied.
        This is only needed when submitting to a remote cluster.
        '''
        self.tasks = list()
        self.experiment = experiment
        self.no_shared_network = no_shared_network
        self.virtualenv = virtualenv

    @cached_property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir, 'tmaps')
        if not os.path.exists(self._project_dir):
            os.mkdir(self._project_dir)
        return self._project_dir

    def add_step(self, prog_name, main_args, init_args):
        '''
        Add an additional step to the workflow,
        i.e. extend the list of *tasks*.

        Parameters
        ----------
        prog_name: str
            name of the program (command line tool)
        main_args: List[str]
            arguments required for the main parser
        init_args: List[str]
            arguments required for the `init` subparser

        Note
        ----
        The method dynamically loads the *argparser.py* and *cli.py* modules
        of the subpackage corresponding to `prog_name`. The name of the command
        line interface class in *cli.py must be the same as `prog_name` with
        capital first letter.
        '''
        package_name = 'tmlib'

        argparser_module_name = '%s.%s.argparser' % (package_name, prog_name)
        logger.debug('load module "%s"' % argparser_module_name)
        argparser_module = importlib.import_module(argparser_module_name)
        parser = argparser_module.parser
        parser.prog = prog_name
        cli_module_name = '%s.%s.cli' % (package_name, prog_name)
        logger.debug('load module "%s"' % cli_module_name)
        cli_module = importlib.import_module(cli_module_name)

        init_command = list()
        init_command.extend(main_args)
        init_command.append(self.experiment.dir)
        init_command.append('init')
        init_command.extend(init_args)
        args = parser.parse_args(init_command)
        cli_class_name = prog_name.capitalize()
        cli_class_inst = getattr(cli_module, cli_class_name)(args)
        cli_class_inst.init()

        submit_command = list()
        submit_command.extend(main_args)
        submit_command.append(self.experiment.dir)
        submit_command.append('submit')
        if self.no_shared_network:
            submit_command.append('--no_shared_network')
        if self.virtualenv:
            submit_command.extend(['--virtualenv', self.virtualenv])
        args = parser.parse_args(submit_command)

        cli_class_inst = getattr(cli_module, prog_name.capitalize())(args)
        task = cli_class_inst.get_jobs()
        self.tasks.append(task)

    def create_jobs(self):
        '''
        Create a GC3Pie task collection of "jobs" for all *steps* that have
        them added.

        Returns
        -------
        gc3libs.workflow.SequentialTaskCollection
            jobs
        '''
        # overwrite
        jobs = SequentialTaskCollection(
                    tasks=self.tasks,
                    jobname='tmaps_workflow')
        return jobs


class ClusterWorkflowManager(object):

    '''
    Class for reading workflow descriptions from a YAML file.
    '''

    def __init__(self, experiment_dir):
        '''
        Initialize an instance of class ClusterWorkflowManager.

        Parameters
        ----------
        experiment_dir: str
            path to an experiment directory

        Returns
        -------
        ClusterWorkflowManager
        '''
        self.experiment_dir = os.path.expandvars(experiment_dir)
        self.experiment_dir = os.path.expanduser(self.experiment_dir)
        self.experiment_dir = os.path.abspath(self.experiment_dir)

    @property
    def workflow_file_name(self):
        '''
        Returns
        -------
        str
            absolute path to the *.workflow* file

        Note
        ----
        The file is located in the root directory of the experiment folder.
        '''
        self._workflow_file_name = os.path.join(
                self.experiment_dir,
                '%s.workflow' % os.path.basename(self.experiment_dir))
        return self._workflow_file_name

    @property
    def workflow_description(self):
        '''
        Returns
        -------
        dict
            description of the workflow read from YAML
        '''
        self._workflow_description = utils.read_yaml(self.workflow_file_name)
        for i, step in enumerate(self._workflow_description['steps']):
            self._workflow_description['steps'][i]['prog_args'] = \
                self.format_args(step['prog_args']) + \
                ['-v' for x in xrange(self._workflow_description['verbosity'])]
            self._workflow_description['steps'][i]['init_args'] = \
                self.format_args(step['init_args'])
        return self._workflow_description

    @staticmethod
    def format_args(args):
        '''
        Format arguments as generated by an `argparse.ArgumentParser` instance.

        Parameters
        ----------
        dict
            arguments as key-value pairs, where key is the name of the argument
            and the value the corresponding value of the argument:
            ``{"foo": "bla", "bar": 2}``

        Returns
        -------
        List[str]
            arguments in the format ``["--foo", "bla", "--bar", "2"]``
        '''
        if args:
            arg_list = utils.flatten([
                ['--%s' % k, str(v)]
                for k, v in args.iteritems()
            ])
        else:
            arg_list = list()
        return arg_list

