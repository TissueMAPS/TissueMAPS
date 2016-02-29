// This directive should automatically hide workbench divs whose Workbench object is set to inactive
// The core classes should not explicitly hide or show anything, the UI should instead react to changes of the core classes.
angular.module('tmaps.ui').directive('tmWorkbenchesContainer', [function() {
    return {
        restrict: 'EA',
        controller: [function() {

        }],
        controllerAs: 'workbenchesContainerCtrl',
        bindToController: true
    };
}]);
