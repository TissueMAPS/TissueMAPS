angular.module('tmaps.ui')
.directive('tmToolbar', function() {
    return {
        restrict: 'E',
        scope: {
            appInstance: '='
        },
        controller: 'ToolbarCtrl',
        controllerAs: 'toolbarCtrl',
        templateUrl: '/templates/main/tools/tm-toolbar.html'
    };
});
