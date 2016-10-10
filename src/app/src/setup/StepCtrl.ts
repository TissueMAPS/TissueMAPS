class StepCtrl {

    currentStageIndex: number;
    currentStepIndex: number;
    jobs: any[] = [];

    private _currentJobBatchNr = 0;

    static $inject = ['workflow', 'workflowService', '$state', '$scope', '$uibModal', 'experiment', '$http'];

    constructor(public workflow: Workflow,
                private _workflowService,
                private _$state,
                private _$scope,
                private _$uibModal,
                private _experiment,
                private _$http) {
        this.workflow = this._workflowService.workflow;
        var stageName = this._$state.params.stageName;
        var stepName = this._$state.params.stepName;
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex = stageIndex;
                stage.steps.forEach((step, stepIndex) => {
                    if (step.name == stepName) {
                        this.currentStepIndex = stepIndex;
                    }
                });
            }
        });
        // Get the frist N jobs
        this.requestNextNJobStati();
    }

    hasExtraArgs() {
        var stageIdx = this.currentStageIndex;
        var stepIdx = this.currentStepIndex;
        if (this.workflow.stages[stageIdx].steps[stepIdx] == undefined) {
            return false;
        } else if (this.workflow.stages[stageIdx].steps[stepIdx].extra_args) {
            return true;
        } else {
            return false;
        }
    }

    requestNextNJobStati() {
        var experimentId = this._experiment.id;
        var stepName = this._$state.params.stepName;
        var url = '/api/experiments/' + experimentId + '/workflow/status/jobs' +
                  '?batch=' + this._currentJobBatchNr + '&step_name=' + stepName;
        this._$http.get(url).then((resp) => {
            resp.data.data.forEach((job) => {
                this.jobs.push(job);
            });
            this._currentJobBatchNr += 1;
        });

    }

}

angular.module('tmaps.ui').controller('StepCtrl', StepCtrl);
