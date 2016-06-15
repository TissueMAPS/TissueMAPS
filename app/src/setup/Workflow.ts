class Workflow extends JobCollection {
    stages: WorkflowStage[];

    constructor(workflowDescription: any,
                workflowStatus: any) {

        super(workflowStatus);
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
        var processingStages = workflowDescription.stages.map((stage, index) => {
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
        console.log(index)
        if (index == null) {
            index = this.stages.length - 1;
        }
        return this.stages.every((stage, idx) => {
            if (idx <= index) {
                return stage.check();
            } else {
                // subsequent step which don't get submitted
                // are not checked here
                return true;
            }
        });
    }

}
