angular.module('tmaps.ui')
.directive("tmObjectSettings", function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '='
        },
        bindToController: true,
        controllerAs: 'objCtrl',
        controller: 'ObjectSettingsCtrl',
        templateUrl: '/src/viewer/sidebar/objects/tm-object-settings.html'
    };
});

