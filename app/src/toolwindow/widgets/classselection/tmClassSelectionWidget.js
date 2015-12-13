angular.module('tmaps.toolwindow')
.directive('tmClassSelectionWidget', function() {
    return {
        restrict: 'E',
        templateUrl: '/templates/tools/widgets/tm-class-selection-widget.html',
        controller: 'ClassSelectionWidgetCtrl',
        controllerAs: 'classSelectionWidget'
    };
});
