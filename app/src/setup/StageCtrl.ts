class StageCtrl {

    static $inject = ['stage', '$scope'];

    constructor(public stage: any, private _$scope: any) {}
}

angular.module('tmaps.ui').controller('StageCtrl', StageCtrl);

angular.module('tmaps.ui').directive('tmArgumentInput', function() {
    return {
        restrict: 'E',
        scope: {
            argCollection: '=',
            arg: '='
        },
        controller: ['$scope', function($scope) {
            var inputType, isScalar;

            $scope.argCollection[$scope.arg.name] = $scope.arg.default;
            $scope.isScalar = $scope.arg.choices === null;

            if ($scope.isScalar) {
                if ($scope.arg.type == 'int') {
                    inputType = 'number';
                } else if ($scope.arg.type == 'str') {
                    inputType = 'text';
                }
            }

            $scope.inputType = inputType;
        }],
        templateUrl: '/src/setup/tm-argument-input.html'
    };
})
