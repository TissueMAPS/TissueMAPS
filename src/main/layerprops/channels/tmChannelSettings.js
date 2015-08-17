angular.module('tmaps.main.layerprops.channels')
.directive("tmChannelSettings", function() {
    return {
        restrict: 'E',
        scope: {
            appInstance: '='
        },
        controller: 'ChannelSettingsCtrl',
        controllerAs: 'channelsCtrl',
        templateUrl: '/templates/main/layerprops/channels/tm-channel-settings.html'
    };
});
