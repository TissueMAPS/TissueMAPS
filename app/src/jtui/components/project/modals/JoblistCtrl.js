angular.module('jtui.project')
.controller('JoblistCtrl', ['$scope', 'joblist', '$modalInstance',
    function($scope, joblist, $modalInstance) {

    $scope.joblist = joblist;
    console.log('joblist:', joblist)

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
