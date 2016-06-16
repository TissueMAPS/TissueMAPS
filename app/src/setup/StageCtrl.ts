class StageCtrl {
    currentStageIndex: number
    currentStepIndex: number;

    static $inject = ['workflow', 'workflowService', '$state', '$scope'];

    constructor(public workflow: Workflow,
                private _workflowService,
                private _$state,
                private _$scope) {
        // console.log(this.workflow)
        this.workflow = this._workflowService.workflow;
        // this._$scope.$watch('stageCtrl.workflow', (updatedWorkflow) => {
        //     console.log(updatedWorkflow.status)
        // }, true);
        // TODO: stageName incorrect when reloading
        var stageName = this._$state.params.stageName;
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex = stageIndex;
            }
        })
        // this._$scope.$watch('setupCtrl.currentStage');
        var idx = this.currentStageIndex;
        if (this.workflow.stages[idx] == undefined) {
            // TODO: different plates instead of steps?
            this._$state.go('plate');
        } else {
            this.goToStep(this.workflow.stages[idx].steps[0]);
        }
    }

    isInStep(step: WorkflowStep) {
        var idx = this.currentStepIndex;
        return this.workflow.stages[this.currentStageIndex].steps[idx].name === step.name;
    }

    goToStep(step: WorkflowStep) {
        var idx = this.currentStageIndex;
        this.currentStepIndex = this.workflow.stages[idx].steps.indexOf(step);
        this._$scope.$watch('stageCtrl.currentStepIndex')
        // console.log('go to step: ', step)
        this._$state.go('setup.step', {
            stepName: step.name
        });
    }

}

angular.module('tmaps.ui').controller('StageCtrl', StageCtrl);

angular.module('tmaps.ui').directive('tmArgumentInput', function() {
    return {
        restrict: 'E',
        scope: {
            arg: '='
        },
        controller: ['$scope', function($scope) {
            var widgetType;
            var argumentType = $scope.arg.type;
            var hasChoices = $scope.arg.choices !== null;

            if (hasChoices && argumentType == 'bool') {
                widgetType = 'checkbox';
            } else if (hasChoices && argumentType !== 'bool') {
                widgetType = 'dropdown';
            } else if (!hasChoices && argumentType === 'int') {
                widgetType = 'numberInput';
            } else if (!hasChoices && argumentType == 'str') {
                widgetType = 'textInput';
            }

            if ($scope.arg.value == null) {
                $scope.arg.value = $scope.arg.default;
            }
            $scope.arg.required = $scope.arg.required || $scope.arg.default !== null;
            $scope.widgetType = widgetType;

            $scope.shouldAlert = function() {
                return $scope.arg.required &&
                       ($scope.arg.value === undefined ||
                        $scope.arg.value === '' ||
                        $scope.arg.value === null);
            };
        }],
        templateUrl: '/src/setup/tm-argument-input.html'
    };
})
