angular.module('tmaps.main.tools')
/**
 * ToolbarCtrl is a controller that manages the list of buttons with which
 * different tools may be accessed. This controller concerns itself with
 * what happens when such a button is pressed.
 */
.controller('ToolbarCtrl',
            ['$scope', 'application', 'appstateService',
            function($scope, application, appstateService) {

    // Add the tools to scope as soon as they are ready
    $scope.tools = [];
    application.getActiveInstance().tools.then(function(tools) {
        $scope.tools = tools;
        window.tools = tools;
    });

    /**
     * This function is called when the Tool's button is pressed.
     */
    $scope.openTool = function(tool) {
        if (appstateService.stateHasBeenSavedAlready()) {
            var appstate = appstateService.currentState;
            var experimentId = $scope.appInstance.experiment.id;
            tool.openWindow(appstate);
        } else {
            throw new Error('Can\'t open window when appstate hasn\'t been saved');
        }
    };
}]);

