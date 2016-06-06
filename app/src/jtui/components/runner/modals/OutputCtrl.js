angular.module('jtui.runner')
.controller('OutputCtrl', ['$scope', '$sce', 'output', 'name', 'jobId',  '$uibModalInstance',
    function ($scope, $sce, output, name, jobId, $uibModalInstance) {

    $scope.output = output;
    $scope.name = name;
    $scope.jobId = jobId;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
