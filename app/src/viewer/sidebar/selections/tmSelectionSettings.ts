angular.module('tmaps.ui')
.directive('tmSelectionSettings', function() {
    return {
        restrict: 'E',
        // Create a new scope for this directive but prototypically link
        // it with the parent viewport scope, s.t. the directive has access
        // to the appInstance.
        scope: true,
        bindToController: true,
        controllerAs: 'selCtrl',
        controller: 'SelectionSettingsCtrl',
        templateUrl: '/templates/main/layerprops/selections/tm-selection-settings.html'
    };
});
