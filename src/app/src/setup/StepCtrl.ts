class StepCtrl {

    currentStageIndex: number;
    currentStepIndex: number;

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

    jobsDataSource = {
        get: (index, count, success) => {
            console.log(index);
            var experimentId = this._experiment.id;
            var stepName = this._$state.params.stepName;
            var url = '/api/experiments/' + experimentId + '/workflow/status/jobs' +
                      '?index=' + index + '&step_name=' + stepName + '&batch_size=' + count;
            this._$http.get(url).then((resp) => {
                var jobs = resp.data.data;
                success(jobs);
            });
        }
    };

}

angular.module('tmaps.ui').controller('StepCtrl', StepCtrl);
