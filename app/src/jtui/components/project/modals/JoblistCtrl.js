angular.module('jtui.project')
.controller('JoblistCtrl', ['$scope', 'joblist', '$uibModalInstance',
    function($scope, joblist, $uibModalInstance) {

    $scope.joblist = joblist;
    console.log('joblist:', joblist)

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

}]);
