angular.module('tmaps.tools.modules.cluster')
.controller('ClusterCtrl', ['$scope', 'toolInstance', function($scope, toolInstance) {
    $scope.sendRequest = function() {
        toolInstance.sendRequest({
            request_type: 'perform_clustering',
            features: $scope.selectedFeatures,
            k: $scope.k
        }).then(function(msg) {
            console.log(msg);
        });
    };
}]);
