angular.module('tmaps.tools.modules.svm')
.controller('SVMCtrl', ['$scope', '$rootScope', 'tmapsProxy', 'toolInstance',
            function($scope, $rootScope, tmapsProxy, toolInstance) {

    $scope.selections = tmapsProxy.viewport.selectionHandler.selections;
    $scope.numClasses = $scope.selections.length;

    $scope.sendRequest = function() {
        var cls = $scope.classes;
        var payload = {
            request_type: 'fit_model',
            training_cell_ids: cls,
            selected_features: $scope.selectedFeatures
        };

        toolInstance.sendRequest(payload).then(function(response) {
            // console.log(response);
        });
    };

}]);
