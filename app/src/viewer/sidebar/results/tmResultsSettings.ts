angular.module('tmaps.ui')
.directive('tmResultsSettings', function() {
    return {
        restrict: 'E',
        scope: {
            results: '=',
            viewer: '='
        },
        bindToController: true,
        controllerAs: 'resultsSettingsCtrl',
        controller: 'ResultsSettingsCtrl',
        templateUrl: '/src/viewer/sidebar/results/tm-results-settings.html'
    };
});

