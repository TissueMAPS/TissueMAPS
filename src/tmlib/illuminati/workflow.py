from gc3libs.workflow import SequentialTaskCollection


class MultiRunJobCollection(SequentialTaskCollection):

    def __init__(self, step_name, run_job_collections):
        '''
        Initialize an instance of class WorkflowStep.

        Parameters
        ----------
        step_name: str
            name of the corresponding TissueMAPS workflow step
        run_job_collections: List[tmlib.tmaps.workflow.RunJobCollection]
            several collections of run jobs that should be processed one
            after the other
        '''
        self.step_name = step_name
        super(MultiRunJobCollection, self).__init__(
                    tasks=run_job_collections,
                    jobname='%s_multirun' % step_name)
