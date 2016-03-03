interface ToolbarScope extends ViewerScope {

}

/**
 * ToolbarCtrl is a controller that manages the list of buttons with which
 * different tools may be accessed. This controller concerns itself with
 * what happens when such a button is pressed.
 */
class ToolbarCtrl {
    static $inject = ['$scope', 'application', 'appstateService', 'authService'];

    tools: Tool[] = [];

    constructor(public $scope: ToolbarScope,
                private application: Application,
                private appstateService,
                private authService) {
        // Add the tools as soon as they are ready
        this.$scope.viewer.tools.then((tools) => {
            this.tools = tools;
        });
    }

    /**
     * The Toolbar should only be visible when the user is logged in and the
     * appstate isn't marked as being a snapshot.
     */
    isToolbarVisible(): boolean {
        var userIsViewingSnapshot = this.appstateService.getCurrentState().isSnapshot;
        var userIsAuthenticated = this.authService.isUserAuthenticated();
        return userIsAuthenticated && !userIsViewingSnapshot;
    };

    /**
     * This function is called when the Tool's button is pressed.
     */
    clickToolTab(tool: Tool) {
        var sess = tool.createSession();
        this.$scope.viewerWindowCtrl.$scope.$broadcast('clickToolbarTab', {
            tool: tool,
            session: sess
        });
    }
}
angular.module('tmaps.ui').controller('ToolbarCtrl', ToolbarCtrl);
