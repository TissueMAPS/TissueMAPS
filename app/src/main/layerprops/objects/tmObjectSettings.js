angular.module('tmaps.main.layerprops.objects')
.directive("tmObjectSettings", function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '='
        },
        bindToController: true,
        controllerAs: 'objCtrl',
        controller: 'ObjectSettingsCtrl',
        templateUrl: '/src/main/layerprops/objects/tm-object-settings.html'
    };
});

