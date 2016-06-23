angular.module('jtui.runner')
.controller('LogCtrl', ['$scope', 'log', 'jobId', '$uibModalInstance',
    function($scope, log, jobId, $uibModalInstance) {

    $scope.log = log;
    $scope.jobId = jobId;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
