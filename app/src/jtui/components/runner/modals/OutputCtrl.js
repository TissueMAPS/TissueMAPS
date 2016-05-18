angular.module('jtui.runner')
.controller('OutputCtrl', ['$scope', '$sce', 'output', '$modalInstance',
    function ($scope, $sce, output, $modalInstance) {

    $scope.output = output;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
