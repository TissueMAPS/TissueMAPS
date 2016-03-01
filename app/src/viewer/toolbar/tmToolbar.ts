angular.module('tmaps.ui')
.directive('tmToolbar', function() {
    return {
        restrict: 'E',
        controller: 'ToolbarCtrl',
        controllerAs: 'toolbarCtrl',
        templateUrl: '/src/viewer/toolbar/tm-toolbar.html'
    };
});
