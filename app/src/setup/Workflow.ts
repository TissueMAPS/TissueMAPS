interface WorkflowDescription {
    type: string;
    stages: WorkflowStageDescription[];
}


class Workflow extends JobCollection {
    type: string;
    stages: WorkflowStage[];

    constructor(description: WorkflowDescription,
                workflowStatus: any) {

        super(workflowStatus);
        this.type = description.type;
        var uploadStage = new WorkflowStage({
                name: 'upload',
                steps: [],
                active: true,
                mode: 'sequential'
            }, {
                done: false,
                failed: false,
                percentDone: 0,
                state: '',
                subtasks: []
        });
        var processingStages = description.stages.map((stage, index) => {
            var workflowStageStatus = null;
            if (workflowStatus != null) {
                if (index < workflowStatus.subtasks.length) {
                   workflowStageStatus = workflowStatus.subtasks[index];
                }
            }
            return new WorkflowStage(stage, workflowStageStatus);
        });
        this.stages = [uploadStage].concat(processingStages);
    }

    check(index: number): boolean {
        if (index == null || index == undefined) {
            index = this.stages.length - 1;
        }
        return this.stages.every((stage, idx) => {
            if (idx <= index) {
                console.log(stage.name)
                return stage.check();
            } else {
                // subsequent step which don't get submitted
                // are not checked here
                return true;
            }
        });
    }

    serialize(index: number): WorkflowDescription {
        return {
            type: this.type,
            stages: this.stages.map((stage, idx) => {
                var serializedStage = stage.serialize();
                if (index < idx) {
                    serializedStage.active = true;
                } else {
                    serializedStage.active = false;
                }
                return serializedStage;
            })
        }
    }

}
