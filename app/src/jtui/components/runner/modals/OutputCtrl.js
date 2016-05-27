angular.module('jtui.runner')
.controller('OutputCtrl', ['$scope', '$sce', 'output', '$uibModalInstance',
    function ($scope, $sce, output, $uibModalInstance) {

    $scope.output = output;

    $scope.close = function (result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
