class StepCtrl {
    step: WorkflowStep;

    static $inject = ['$state', '$scope', '$uibModal'];

    constructor(private _$state,
                private _$scope,
                private _$uibModal) {
        this.step = this._$scope.stageCtrl.currentStep;
        this._$scope.$watch('stageCtrl.currentStep');
    }

    goToJobStatus() {
        console.log('go to job status')
        this._$state.go('setup.jobs', {});
    }

    getLogOuput(job: Job) {
        console.log('get log output')
    }

}

angular.module('tmaps.ui').controller('StepCtrl', StepCtrl);
