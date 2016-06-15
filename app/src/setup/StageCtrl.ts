class StageCtrl {
    stage: WorkflowStage;
    currentStep: WorkflowStep;

    static $inject = ['$state', '$scope', '$rootScope'];

    constructor(private _$state: any,
                private _$scope: any) {
        this.stage = this._$scope.setupCtrl.currentStage;
        this._$scope.$watch('setupCtrl.currentStage');
        if (this.stage == undefined) {
            // TODO: different plates instead of steps?
            this._$state.go('plate');
        } else {
            this.goToStep(this.stage.steps[0]);
        }
    }

    isInStep(step: WorkflowStep) {
        return this.currentStep.name === step.name;
    }

    goToStep(step: WorkflowStep) {
        this.currentStep = step;
        // console.log('go to step: ', this.currentStep)
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
