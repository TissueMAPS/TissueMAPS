angular.module('tmaps.ui')
.directive('tmVisualLayerSettings', function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '='
        },
        bindToController: true,
        controllerAs: 'visualLayerCtrl',
        controller: 'VisualLayerSettingsCtrl',
        templateUrl: '/src/viewer/sidebar/visuallayers/tm-visuallayer-settings.html'
    };
});

