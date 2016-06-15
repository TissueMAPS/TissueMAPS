class WorkflowStage extends JobCollection {
    name: string;
    active: boolean;
    mode: string;
    steps: WorkflowStep[];

    constructor(workflowStageDescription: any,
                workflowStageStatus: any) {
        super(workflowStageStatus);
        this.name = workflowStageDescription.name;
        if (workflowStageDescription.steps != null) {
            // NOTE: due to hack for "upload" stage, which doens't have any steps
            this.steps = workflowStageDescription.steps.map((step, index) => {
                var workflowStepStatus = null;
                if (workflowStageStatus != null) {
                    workflowStepStatus = workflowStageStatus.subtasks[index];
                }
                return new WorkflowStep(step, workflowStepStatus);
            });
        }
    }

    private _isUploadOk() {
        return this.status.done && !this.status.failed;
        // var atLeastOnePlate = this.plates.length > 0;
        // var allPlatesReady = _.all(this.plates.map((pl) => {
        //     return pl.isReadyForProcessing;
        // }));
        // return atLeastOnePlate && allPlatesReady;
    }

    check(): boolean {
        if (this.name == 'upload') {
            return this._isUploadOk();
        }
        var workflowStatusArgsAreValid, batchArgsAreValid, extraArgsAreValid;
        var isValid: boolean;

        function checkArgs(args) {
            return _.chain(args).map((arg) => {
                var isValid;
                if (arg.required) {
                    isValid = arg.value !== undefined
                        && arg.value !== null
                        && arg.value !== '';
                } else {
                    isValid = true;
                }
                return isValid;
            }).all().value();
        }

        var areStepsOk: boolean[] = this.steps.map((step) => {
            batchArgsAreValid = checkArgs(step.batch_args);
            workflowStatusArgsAreValid = checkArgs(step.submission_args);

            if (step.extra_args) {
                extraArgsAreValid = checkArgs(step.extra_args);
            } else {
                extraArgsAreValid = true;
            }

            return batchArgsAreValid && workflowStatusArgsAreValid && extraArgsAreValid;
        });
        return _.all(areStepsOk);
    }

}

