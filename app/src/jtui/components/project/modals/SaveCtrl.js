angular.module('jtui.project')
.controller('SaveCtrl', ['$scope', 'saved',
    function($scope, saved) {

    $scope.saved = saved.success;
    $scope.error = saved.error;

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
