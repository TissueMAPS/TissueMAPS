angular.module('tmaps.ui')
.directive("tmChannelSettings", function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '='
        },
        controller: 'ChannelSettingsCtrl',
        controllerAs: 'channelsCtrl',
        bindToController: true,
        templateUrl: '/templates/main/layerprops/channels/tm-channel-settings.html'
    };
});
