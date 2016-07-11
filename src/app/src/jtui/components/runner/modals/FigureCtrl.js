angular.module('jtui.runner')
.controller('FigureCtrl', ['$scope', '$sce', 'figure', 'name', 'jobId', '$uibModalInstance',
    function($scope, $sce, figure, name, jobId, $uibModalInstance) {

    $scope.figure = figure;
    $scope.figure.layout.height = 1000;
    $scope.figure.layout.width = 1000;
    // $scope.figure.layout.width = '100%';
    $scope.figure.options = {
        showLink: false,
        displayLogo: false,  // this doesn't work
        displayModeBar: true,
    };
    $scope.name = name;
    $scope.jobId = jobId;

    console.log($scope.figure)

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
