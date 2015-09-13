angular.module('tmaps.main.layerprops.objects')
.controller('ObjectSettingsCtrl',
            ['$scope', function($scope) {

    this.layers = this.appInstance.objectLayers;

    this.removeLayer = function(layer) {
        this.appInstance.removeObjectLayer(layer);
    };

}]);

