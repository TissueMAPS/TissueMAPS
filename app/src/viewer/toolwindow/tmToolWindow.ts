interface ToolWindowScope extends ViewerScope {
    toolWindowCtrl: ToolWindowCtrl;
    tool: Tool;
    session: ToolSession;
}

class ToolWindowCtrl {
    static $inject = ['$scope'];

    sessionElements: {[sessionId: string]: JQuery} = {};

    constructor(public $scope: ToolWindowScope) {
        $scope.viewerWindowCtrl.$scope.$on('clickToolbarTab', (evt, data) => {
            this.$scope.tool = data.tool;
            this.$scope.session = data.session;
        });
    }

    showToolSession(session: ToolSession) {
        // var s: ToolSession;
        // if (this.sessionElements[session.id] === undefined) {
        //     this.sessionElements[session.id] = session;
        //     s = session;
        // } else {
        //     s = this.sessionElements[sess.id];
        // }
    }
}
angular.module('tmaps.ui').controller('ToolWindowCtrl', ToolWindowCtrl);

angular.module('tmaps.ui')
.directive('tmToolWindow', () => {
    return {
        templateUrl: '/src/viewer/toolwindow/tool-window.html',
        controller: 'ToolWindowCtrl',
        controllerAs: 'toolWindowCtrl'
    };
})
