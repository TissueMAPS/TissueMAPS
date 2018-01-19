import logging
import gc3libs
from abc import ABCMeta
from abc import abstractproperty

from tmlib.utils import create_datetimestamp

logger = logging.getLogger(__name__)


class Job(gc3libs.Application):

    '''Abstract base class for a job, which can be submitted for processing
    on different cluster backends.
    '''

    __meta__ = ABCMeta

    def __init__(self, arguments, output_dir, submission_id, user_name,
                 parent_id=None, **extra_args):
        '''
        Parameters
        ----------
        arguments: List[str]
            command line arguments
        output_dir: str
            absolute path to the output directory, where log reports will
            be stored
        submission_id: int
            ID of the corresponding submission
        user_name: str
            name of the submitting user
        parent_id: int, optional
            ID of the parent job collection
        **extra_args
            Any additional keyword arguments are passed unchanged
            to the parent class constructor
        '''
        t = create_datetimestamp()
        self.user_name = user_name
        self.submission_id = submission_id
        self.parent_id = parent_id
        super(Job, self).__init__(
            jobname=self.name,
            arguments=arguments,
            output_dir=output_dir,
            stdout='%s_%d_%s.out' % (self.name, self.submission_id, t),
            stderr='%s_%d_%s.err' % (self.name, self.submission_id, t),
            # Assumes that nodes have access to a shared file system.
            inputs=[],
            outputs=[],
            # pass extra arguments up to superclass ctor
            **extra_args
        )

    def sbatch(self, resource, **kwargs):
        '''Overwrites the original `sbatch` method to enable
        `fair-share scheduling on SLURM backends <http://slurm.schedmd.com/priority_multifactor.html>`_.

        See also
        --------
        :meth:`gc3libs.Application.sbatch`

        Note
        ----
        User accounts must be registered in the
        `SLURM accounting database <http://slurm.schedmd.com/accounting.html>`_.
        '''
        sbatch, cmdline = super(Job, self).sbatch(resource, **kwargs)
        sbatch += ['--account', self.user_name]
        return (sbatch, cmdline)

    @abstractproperty
    def name(self):
        '''str: name of the job'''
        pass

    def retry(self):
        '''Decides whether the job should be retried.

        Returns
        -------
        bool
            whether job should be resubmitted
        '''
        # TODO
        return super(Job, self).retry()

    @property
    def is_terminated(self):
        '''bool: whether the job is in state TERMINATED'''
        return self.execution.state == gc3libs.Run.State.TERMINATED

    @property
    def is_running(self):
        '''bool: whether the job is in state RUNNING'''
        return self.execution.state == gc3libs.Run.State.RUNNING

    @property
    def is_stopped(self):
        '''bool: whether the job is in state STOPPED'''
        return self.execution.state == gc3libs.Run.State.STOPPED

    @property
    def is_submitted(self):
        '''bool: whether the job is in state SUBMITTED'''
        return self.execution.state == gc3libs.Run.State.SUBMITTED

    @property
    def is_new(self):
        '''bool: whether the job is in state NEW'''
        return self.execution.state == gc3libs.Run.State.NEW

    def __repr__(self):
        return (
            '<%s(name=%r, submission_id=%r)>'
            % (self.__class__.__name__, self.name, self.submission_id)
        )
