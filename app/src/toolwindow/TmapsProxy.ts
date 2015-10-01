interface ToolWindowInitObject {
    appInstance: AppInstance;
    viewportScope: ViewportElementScope;
    applicationScope: ng.IScope;
    tool: Tool;
    toolWindow: ToolWindow;
}

interface ToolWindowObject extends ng.IWindowService {
    init: ToolWindowInitObject;
}

class TmapsProxy {
    static $inject = ['$window'];

    appInstance: AppInstance;
    viewportScope: ViewportElementScope;
    applicationScope: ng.IScope;
    tool: Tool;
    toolWindow: ToolWindow;

    constructor(private $window: ToolWindowObject) {
        if (angular.isDefined($window.init)) {
            this.appInstance = $window.init.appInstance;
            this.viewportScope = $window.init.viewportScope;
            this.applicationScope = $window.init.applicationScope;
            this.tool = $window.init.tool;
            this.toolWindow = $window.init.toolWindow;
        } else {
            console.log('No init object on the global scope!');
        }
    }
}

angular.module('tmaps.toolwindow').service('tmapsProxy', TmapsProxy);
