angular.module('jtui.project')
.controller('CheckCtrl', ['$scope', 'checked',
    function($scope, checked) {

    $scope.checked = checked.success;
    $scope.error = checked.error;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
