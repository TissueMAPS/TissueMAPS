angular.module('tmaps.toolwindow')
/**
 * A directive with which features can be selected.
 *
 * Example usage:
 *
 *  <tm-feature-selection-widget></tm-feature-selection-widget>
 */
.directive('tmFeatureSelectionWidget', function() {
    return {
        restrict: 'E',
        templateUrl: '/templates/tools/widgets/tm-feature-selection-widget.html',
        controller: 'FeatureSelectionWidgetCtrl',
        controllerAs: 'featureWidget',
        bindToController: true,
        scope: {
            name: '@name',
            maxSelections: '@maxSelections'
        }
    };
});
