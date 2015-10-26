import os
import logging
from ..cluster import BasicClusterRoutines

logger = logging.getLogger(__name__)


class WorkflowClusterRoutines(BasicClusterRoutines):

    def __init__(self, experiment, prog_name):
        '''
        Initialize an instance of class WorkflowClusterRoutines.

        Parameters
        ----------
        experiment: tmlib.experiment.Experiment
            configured experiment object
        prog_name: str
            name of the corresponding program (command line interface)
        '''
        super(WorkflowClusterRoutines, self).__init__(experiment)
        self.experiment = experiment
        self.prog_name = prog_name

    @property
    def project_dir(self):
        '''
        Returns
        -------
        str
            directory where *.job* files and log output will be stored
        '''
        self._project_dir = os.path.join(self.experiment.dir, self.prog_name)
        if not os.path.exists(self._project_dir):
            logging.debug('create project directory: %s' % self._project_dir)
            os.mkdir(self._project_dir)
        return self._project_dir
