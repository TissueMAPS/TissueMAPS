angular.module('jtui.handles')
.controller('HandlesHelpCtrl', ['$scope', 'help', '$modalInstance',
    function($scope, help, $modalInstance) {

    $scope.help = help;
    console.log('help:', help)

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
