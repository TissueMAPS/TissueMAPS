class StageCtrl {

    static $inject = ['stage', '$scope'];

    constructor(public stage: any, private _$scope: any) {
        this._$scope.setupCtrl.currentStage = stage;
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
