angular.module('tmaps.toolwindow')
.controller('SVMCtrl', ['$scope', '$rootScope', 'tmapsProxy',
            function($scope, $rootScope, tmapsProxy) {

    // $scope.selections = tmapsProxy.viewport.selectionHandler.selections;
    // $scope.numClasses = $scope.selections.length;

    $scope.sendRequest = function() {
        // var cls = $scope.classes;
        // var payload = {
        //     request_type: 'fit_model',
        //     training_cell_ids: cls,
        //     selected_features: $scope.selectedFeatures
        // };
        var payload = {
            message: 'o hai there'
        };

        tmapsProxy.tool.sendRequest(payload).then(function(response) {

        });
    };

}]);
