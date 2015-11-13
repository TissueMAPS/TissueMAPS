angular.module('tmaps.toolwindow')
.controller('SVMCtrl', ['$scope', '$rootScope', 'tmapsProxy',
            function($scope, $rootScope, tmapsProxy) {

    $scope.selections = tmapsProxy.appInstance.viewport.selectionHandler.selections;

    $scope.sendRequest = function() {
        var cls = $scope.classes;
        var payload = {
            request_type: 'fit_model',
            training_cell_ids: cls,
            selected_features: $scope.selectedFeatures
        };
        console.log(cls);

        tmapsProxy.tool.sendRequest(payload).then(function(response) {
            console.log(response);
        });
    };

}]);
