angular.module('tmaps.ui')
.controller('ChannelSettingsCtrl',
            ['$scope', function($scope) {

    this.layers = $scope.viewport.channelLayers;

}]);
