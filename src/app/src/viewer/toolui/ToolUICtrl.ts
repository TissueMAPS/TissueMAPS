interface ToolUIScope extends ViewerScope {
    toolUICtrl: ToolUICtrl;
}

class ToolUICtrl {
    static $inject = ['$scope'];

    showWindow: boolean = false;
    currentTool: Tool;
    currentSession: ToolSession;

    constructor(private $scope: ng.IScope) {
        
    }

    hideWindow() {
        this.showWindow = false;
    }

    toggleToolWindow(tool: Tool) {
        var isSessionDefined = this.currentSession !== undefined;
        var doShowWindow = !isSessionDefined || isSessionDefined && this.showWindow === false;

        if (doShowWindow) {
            this.currentTool = tool;
            if (tool.sessions.length == 0) {
                this.currentSession = tool.createSession();
            } else {
                this.currentSession = tool.sessions[tool.sessions.length - 1];
            }
            this.showWindow = true;
        } else {
            this.showWindow = false;
        }
    }

}

angular.module('tmaps.ui').controller('ToolUICtrl', ToolUICtrl);
