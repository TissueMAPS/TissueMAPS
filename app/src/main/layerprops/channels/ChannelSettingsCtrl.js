angular.module('tmaps.main.layerprops.channels')
.controller('ChannelSettingsCtrl',
            ['$scope', function($scope) {

    this.layers = $scope.viewport.channelLayers;

}]);
