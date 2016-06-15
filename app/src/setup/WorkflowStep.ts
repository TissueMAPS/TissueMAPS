interface WorkflowStepDescription {
    name: string;
    active: boolean;
    batch_args: any;
    submission_args: any;
    extra_args: any;
}


class WorkflowStep extends JobCollection {
    name: string;
    active: boolean;
    batch_args: Argument[];
    submission_args: Argument[];
    extra_args: Argument[];
    jobs: Job[];

    constructor(description: WorkflowStepDescription,
                workflowStepStatus: any) {
        super(workflowStepStatus);
        this.name = description.name;
        this.active = description.active;
        this.batch_args = description.batch_args.map((arg) => {
            return new Argument(arg);
        });
        this.submission_args = description.submission_args.map((arg) => {
            return new Argument(arg);
        });
        if (description.extra_args != null) {
            this.extra_args = description.extra_args.map((arg) => {
                return new Argument(arg);
            });
        }
    }

    getDescription(): WorkflowStepDescription {
        return {
            name: this.name,
            batch_args: this.batch_args,
            submission_args: this.submission_args,
            extra_args: this.extra_args,
            active: this.active
        }
    }
}
