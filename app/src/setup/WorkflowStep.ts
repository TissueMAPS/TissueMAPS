interface WorkflowStepDescription {
    name: string;
    active: boolean;
    batch_args: any;
    submission_args: any;
    extra_args: any;
    fullname: string;
    help: string;
}


class WorkflowStep extends JobCollection {
    name: string;
    active: boolean;
    batch_args: Argument[];
    submission_args: Argument[];
    extra_args: Argument[];
    jobs: Job[];
    fullname: string;
    help: string;

    constructor(description: WorkflowStepDescription,
                workflowStepStatus: any) {
        super(workflowStepStatus);
        this.name = description.name;
        this.active = description.active;
        this.fullname = description.fullname;
        this.help = description.help;
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
        this.jobs = [];
        if (workflowStepStatus != null) {
            workflowStepStatus.subtasks.map((phase, index) => {
                if (phase.subtasks.length > 0) {
                    phase.subtasks.map((subphase, index) => {
                        if (subphase.subtasks.length > 0) {
                            subphase.subtasks.map((job) => {
                                this.jobs.push(new Job(job));
                            });
                        } else {
                            this.jobs.push(new Job(subphase));
                        }
                    });
                } else {
                    this.jobs.push(new Job(phase));
                }
            });
        }
    }

    getDescription(): WorkflowStepDescription {
        return {
            name: this.name,
            batch_args: this.batch_args,
            submission_args: this.submission_args,
            extra_args: this.extra_args,
            active: this.active,
            help: this.help,
            fullname: this.fullname
        }
    }
}
