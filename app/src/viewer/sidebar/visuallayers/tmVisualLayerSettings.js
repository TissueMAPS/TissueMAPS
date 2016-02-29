angular.module('tmaps.ui')
.directive('tmVisualLayerSettings', function() {
    return {
        restrict: 'E',
        scope: {
            viewport: '=',
            contentType: '='
        },
        bindToController: true,
        controllerAs: 'visualLayerCtrl',
        controller: 'VisualLayerSettingsCtrl',
        templateUrl: '/src/ui/sidebar/visuallayers/tm-visuallayer-settings.html'
    };
});

