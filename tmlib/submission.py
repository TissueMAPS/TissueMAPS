import logging
import tmlib.models as tm


class SubmissionManager(object):

    '''Mixin class for submission and monitoring of computational tasks.'''

    def __init__(self, experiment_id, program_name):
        '''
        Parameters
        ----------
        experiment_id: int
            ID of the processed experiment
        program_name: str
            name of the submitting program
        '''
        self.experiment_id = experiment_id
        self.program_name = program_name

    def register_submission(self, user_id=None):
        '''Creates a database entry in the "submissions" table.

        Parameters
        ----------
        user_id: int, optional
            ID of submitting user (if not the user who owns the experiment)

        Returns
        -------
        Tuple[int, str]
            ID of the submission and the name of the submitting user

        Warning
        -------
        Ensure that the "submissions" table get updated once the jobs
        were submitted, i.e. added to a running `GC3Pie` engine.
        To this end, use the ::meth:`tmlib.workflow.api.update_submission`
        method.

        See also
        --------
        :class:`tmlib.models.submission.Submission`
        '''
        with tm.utils.MainSession() as session:
            if user_id is None:
                experiment = session.query(tm.ExperimentReference).\
                    get(self.experiment_id)
                user_id = experiment.user_id
            submission = tm.Submission(
                experiment_id=self.experiment_id, program=self.program_name,
                user_id=user_id
            )
            session.add(submission)
            session.commit()
            return (submission.id, submission.user.name)


