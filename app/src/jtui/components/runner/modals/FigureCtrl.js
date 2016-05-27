angular.module('jtui.runner')
.controller('FigureCtrl', ['$scope', '$sce', 'figure', 'name', '$uibModalInstance',
    function($scope, $sce, figure, name, $uibModalInstance) {

    console.log('figure: ', figure)
    $scope.figure = figure;
    $scope.figure.options = {showLink: false, displayLogo: false};
    $scope.name = name;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
