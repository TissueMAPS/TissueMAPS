angular.module('tmaps.ui')
.controller('AddExperimentCtrl', ['$scope', '$modalInstance', '$http',
    function($scope, $modalInstance, $http) {

    $scope.experiments = [];

    $http.get('/experiments').then(function(resp) {
        $scope.experiments = resp.data.owned.concat(resp.data.shared);
        console.log(resp.data);
    });

    $scope.getSelected = function() {
        // Filter through experiments and then through the layer array
        // and "forward" each selected experiment (with only the selected layers)
        // for creation of app instances.
        var experiments = $scope.experiments.filter(function(e) {
            return e.selected;
        });

        experiments = _.map(experiments, function(e) {
            e.layers = _.filter(e.layers, function(l) {
                return l.selected;
            });
            return e;
        });

        return experiments;
    };

    $scope.close = function(result) {
        // close, but give 500ms for bootstrap to animate
        close(result, 500);
    };

    $scope.toggleAllSelected = function(index) {
        var exp = $scope.experiments[index];
        exp.layers.forEach(function(layer) {
            layer.selected = exp.selected;
        });
    };
}]);
