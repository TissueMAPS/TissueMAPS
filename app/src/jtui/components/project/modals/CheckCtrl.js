angular.module('jtui.project')
.controller('CheckCtrl', ['$scope', 'checked', '$uibModalInstance',
    function($scope, checked, $uibModalInstance) {

    $scope.checked = checked.success;
    $scope.error = checked.error;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
