angular.module('tmaps.main.layerprops.masks')
.controller('MaskSettingsCtrl',
            ['$scope', function($scope) {

    this.layers = this.viewport.outlineLayers;

}]);
