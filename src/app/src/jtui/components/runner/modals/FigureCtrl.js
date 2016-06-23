angular.module('jtui.runner')
.controller('FigureCtrl', ['$scope', '$sce', 'figure', 'name', 'jobId', '$uibModalInstance',
    function($scope, $sce, figure, name, jobId, $uibModalInstance) {

    $scope.figure = figure;
    $scope.figure.options = {showLink: false, displayLogo: false};
    $scope.name = name;
    $scope.jobId = jobId;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
