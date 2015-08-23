angular.module('tmaps.main.layerprops.selections')
.directive("tmSelectionSettings", function() {
    return {
        restrict: 'E',
        scope: {
            appInstance: '='
        },
        bindToController: true,
        controllerAs: 'selCtrl',
        controller: 'SelectionSettingsCtrl',
        templateUrl: '/templates/main/layerprops/selections/tm-selection-settings.html'
    };
});

