angular.module('jtui.project')
.controller('KillCtrl', ['$scope', 'killed',
    function($scope, killed) {

    $scope.killed = killed.success;
    $scope.error = killed.error;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
