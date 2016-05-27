angular.module('jtui.runner')
.controller('LogCtrl', ['$scope', 'log', '$uibModalInstance',
    function($scope, log, $uibModalInstance) {

    $scope.log = log;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
