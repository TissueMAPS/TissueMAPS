class WorkflowStep extends JobCollection {
    name: string;
    batch_args: Argument[];
    submission_args: Argument[];
    extra_args: Argument[];
    jobs: Job[];

    constructor(workflowStepDescription: any,
                workflowStepStatus: any) {
        super(workflowStepStatus);
        this.name = workflowStepDescription.name;
        this.batch_args = workflowStepDescription.batch_args.map((arg) => {
            return new Argument(arg);
        });
        this.submission_args = workflowStepDescription.submission_args.map((arg) => {
            return new Argument(arg);
        });
        if (workflowStepDescription.extra_args != null) {
            this.extra_args = workflowStepDescription.extra_args.map((arg) => {
                return new Argument(arg);
            });
        }
    }
}
