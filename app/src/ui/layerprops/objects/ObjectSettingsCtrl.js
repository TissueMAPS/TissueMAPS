angular.module('tmaps.ui')
.controller('ObjectSettingsCtrl',
            ['$scope', function($scope) {

    this.layers = this.viewport.objectLayers;

    this.removeLayer = function(layer) {
        this.viewport.removeObjectLayer(layer);
    };

}]);

