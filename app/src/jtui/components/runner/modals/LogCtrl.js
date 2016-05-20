angular.module('jtui.runner')
.controller('LogCtrl', ['$scope', 'log', '$modalInstance',
    function($scope, log, $modalInstance) {

    $scope.log = log;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
