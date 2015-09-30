angular.module('tmaps.tools.modules.cellstats')
.controller('CellStatsCtrl',
            ['$scope', '$rootScope', 'colorUtil', 'toolInstance', 'tmapsProxy',
            function($scope, $rootScope, colorUtil, toolInstance, tmapsProxy) {

    var self = this;
    var expId = tmapsProxy.viewport.experiment.id;

    $scope.featureValues = [];

    this.updateFeatureValues = function(cellId) {
        var payload = {
            get_stats_for_cell_id: cellId
        };
        console.log(payload);
        toolInstance.sendRequest(payload).then(
        function(data) {
            console.log(data);
            $scope.featureValues = data.feature_values;
        },
        function(err) {
            //
        });
    };

    tmapsProxy.$rootScope.$on('clickedOnCell', function(evt, args) {
        console.log(args);
        self.updateFeatureValues(args.cellId);
    });

}]);
