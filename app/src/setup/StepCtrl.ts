class StepCtrl {
    currentStageIndex: number;
    currentStepIndex: number;

    static $inject = ['workflow', 'workflowService', '$state', '$scope', '$uibModal'];

    constructor(public workflow: Workflow,
                private _workflowService,
                private _$state,
                private _$scope,
                private _$uibModal) {
        // console.log(this.workflow)
        this.workflow = this._workflowService.workflow;
        var stageName = this._$state.params.stageName;
        var stepName = this._$state.params.stepName;
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex = stageIndex;
                stage.steps.map((step, stepIndex) => {
                    if (step.name == stepName) {
                        this.currentStepIndex = stepIndex;
                    }
                });
            }
        });
        // this._$scope.$watch('stageCtrl.currentStep');
    }

    goToJobStatus() {
        console.log('go to job status')
        this._$state.go('setup.jobs', {});
    }

}

angular.module('tmaps.ui').controller('StepCtrl', StepCtrl);
