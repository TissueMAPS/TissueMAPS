angular.module('tmaps.main.tools')
/**
 * ToolbarCtrl is a controller that manages the list of buttons with which
 * different tools may be accessed. This controller concerns itself with
 * what happens when such a button is pressed.
 */
.controller('ToolbarCtrl',
            ['$scope', 'toolConfigs', 'toolService', 'appstateService',
            function($scope, toolConfigs, toolService, appstateService) {

    // Add the tools to scope as soon as they are ready
    $scope.tools = [];
    toolConfigs.configs.then(function(configs) {
        $scope.tools = configs;
    });

    /**
     * This function is called when the Tool's button is pressed.
     */
    $scope.openTool = function(tool) {
        if (appstateService.stateHasBeenSavedAlready()) {
            var appstate = appstateService.currentState;
            var experimentId = $scope.appInstance.experiment.id;
            toolService.openWindow(
                tool, $scope.appInstance, appstate.id, experimentId
            );
        } else {
            throw new Error('Can\'t open window when appstate hasn\'t been saved');
        }
    };
}]);

