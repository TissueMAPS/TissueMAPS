interface WorkflowStageDescription {
    name: string;
    active: boolean;
    mode: string;
    steps: WorkflowStepDescription[];
}


class WorkflowStage extends JobCollection {
    name: string;
    active: boolean;
    mode: string;
    steps: WorkflowStep[];

    constructor(description: WorkflowStageDescription,
                workflowStageStatus: any) {
        super(workflowStageStatus);
        this.name = description.name;
        this.mode = description.mode;
        if (description.steps != null) {
            // NOTE: due to hack for "upload" stage, which doens't have any steps
            this.steps = description.steps.map((step, index) => {
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
    }

    check(): boolean {
        if (this.name == 'upload') {
            return this._isUploadOk();
        }
        var areStepsOk: boolean[] = this.steps.map((step) => {
            return step.check();
        });
        return _.all(areStepsOk);
    }

    getDescription(): WorkflowStageDescription {
        return {
            name: this.name,
            mode: this.mode,
            active: this.active,
            steps: this.steps.map((step, idx) => {
                return step.getDescription();
            })
        }
    }
}

