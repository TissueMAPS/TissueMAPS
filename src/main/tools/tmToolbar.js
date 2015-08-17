angular.module('tmaps.main.tools')
.directive('tmToolbar', [function() {

    return {
        restrict: 'E',
        scope: true,
        controller: 'ToolbarCtrl',
        templateUrl: '/templates/main/tools/tm-toolbar.html'
    };
}]);
