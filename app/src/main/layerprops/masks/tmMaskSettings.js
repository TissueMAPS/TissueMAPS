angular.module('tmaps.main.layerprops.masks')
.directive("tmMaskSettings", function() {
    return {
        restrict: 'E',
        scope: {
            appInstance: '='
        },
        bindToController: true,
        controller: 'MaskSettingsCtrl',
        controllerAs: 'masksCtrl',
        templateUrl: '/templates/main/layerprops/masks/tm-mask-settings.html'
    };
});
