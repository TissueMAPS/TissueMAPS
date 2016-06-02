interface Step {
    namn: string;
    extra_args: any[];
    batch_args: any[];
    submit_args: any[];
}

class StageCtrl {

    static $inject = ['stage', '$state', '$scope'];

    constructor(public stage: any,
                private _$state: any,
                private _$scope: any) {
        this._$scope.setupCtrl.currentStage = stage;
    }

    editPipeline(s: Step) {
        var experiment = this._$scope.$parent.setupCtrl.experiment;
        var project = '';
        for (var arg in s.extra_args) {
            if (s.extra_args[arg].name == 'pipeline') {
                project = s.extra_args[arg].value;
            }
        }
        this._$state.go('project', {
            experimentid: experiment.id,
            projectName: project
        });
    }

    createPipeline(s: Step) {
        var experiment = this._$scope.$parent.setupCtrl.experiment;
        var project = '';
        for (var arg in s.extra_args) {
            if (s.extra_args[arg].name == 'pipeline') {
                project = s.extra_args[arg].value;
            }
        }
        // TODO: modal that complains if pipeline does not exist
        this._$state.go('project', {
            experimentid: experiment.id,
            projectName: project
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

            $scope.arg.value = $scope.arg.default;
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
