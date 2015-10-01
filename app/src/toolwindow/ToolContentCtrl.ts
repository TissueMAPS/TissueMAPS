interface ToolContentScope extends ng.IScope {
    tool: Tool;
    isRunning: boolean;
}

angular.module('tmaps.toolwindow')
.controller(
    'ToolContentCtrl',
    ['tmapsProxy', '$scope', '$rootScope',
    function(tmapsProxy: TmapsProxy, $scope: ToolContentScope, $rootScope: ng.IScope) {

    $scope.tool = tmapsProxy.tool;

    $rootScope.$on('toolRequestSent', function() {
        $scope.isRunning = true;
    });

    $rootScope.$on('toolRequestDone', function() {
        $scope.isRunning = false;
    });

}]);
