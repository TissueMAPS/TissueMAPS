angular.module('tmaps.ui')
.directive("tmChannelSettings", function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '='
        },
        controller: 'ChannelSettingsCtrl',
        controllerAs: 'channelsCtrl',
        templateUrl: '/templates/main/layerprops/channels/tm-channel-settings.html'
    };
});
