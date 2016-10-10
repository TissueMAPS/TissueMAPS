angular.module('jtui.project')
.controller('RunCtrl', ['$scope', '$uibModalInstance',
    function($scope, $uibModalInstance) {

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
