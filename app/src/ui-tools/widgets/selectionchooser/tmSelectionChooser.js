angular.module('tmaps.tools.widgets')
.directive('tmSelectionChooser', ['tmapsConfig', function(cfg) {

    return {
        restrict: 'E',
        controller: 'SelectionChooserCtrl',
        templateUrl: '/templates/main/widgets/tm-selection-chooser.html'
    };
}]);

