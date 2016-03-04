interface ToolWindowScope extends ViewerScope {
    toolWindowCtrl: ToolWindowCtrl;
    tool: Tool;
    session: ToolSession;
}

class ToolWindowCtrl {
    static $inject = ['$scope'];

    showWindow: boolean = false;
    tool: Tool;
    session: ToolSession;

    constructor(public $scope: ToolWindowScope) {
        $scope.viewerCtrl.$scope.$on('showToolWindow', (evt, data) => {
            // TODO: It would be nicer if the ToolbarCtrl would actually explicitly
            // tell the toolwindow to hide in case of repeated clicks.
            // The problem why this is not possible in a straightforward manner
            // is that the toolwindow is not a child of the toolbar and thus 
            // the toolbar can't tell if the window is shown or not (in a non-hacky way at elast).
            if (this.session !== undefined &&
                this.showWindow === true &&
                data.session.id === this.session.id) {
                this.showWindow = false;
            } else {
                this.showWindow = true;
                this.tool = data.tool;
                this.session = data.session;
            }
        });

        $scope.viewerCtrl.$scope.$on('hideToolWindow', () => {
            this.showWindow = false;
        });
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

angular.module('tmaps.ui')
.value('toolWindowDOMCache', {})
.directive('tmToolWindowContent',
        ['$controller', '$compile', '$templateRequest', 'toolWindowDOMCache',
        ($controller, $compile, $templateRequest, toolWindowDOMCache) => {
    return {
        restrict: 'A',
        link: function(scope, elem, attr, ctrl) {
            /**
             * Watch the session set in scope and check if it changes to another session.
             * If it does then the old content of this directive should be backed up in 
             * the object toolWindowDOMCache so it can be restored later. This can be useful if
             * the tool window shows a tool result that can't simply be visualized again if the template
             * is included again by ng-include.
             */
            scope.$watch('toolWindowCtrl.session', function(newSession: ToolSession, oldSession: ToolSession) {
                if (newSession === undefined) {
                    return;
                }
                if (oldSession !== undefined && newSession.id === oldSession.id) {
                    return;
                }

                var oldContent = elem.children().get(0);
                if (oldContent) {
                    toolWindowDOMCache[oldSession.id] = oldContent;
                    oldContent.remove();
                }

                var cachedDOMElement = toolWindowDOMCache[newSession.id];
                var hasCachedDOMElement = cachedDOMElement !== undefined;

                if (!hasCachedDOMElement) {
                    var templateUrl = newSession.tool.windowOptions.templateUrl;
                    $templateRequest(templateUrl).then(function(resp) {
                        var newScope = scope.$new();
                        var toolCtrl = $controller(newSession.tool.windowOptions.controller, {
                            viewer: scope.viewer,
                            tool: newSession.tool,
                            $scope: newScope
                        });
                        newScope.toolCtrl = toolCtrl;
                        var newContent = $compile(resp)(newScope)
                        elem.append(newContent);
                    });
                } else {
                    elem.append(toolWindowDOMCache[newSession.id]);
                }

            });

            scope.$on('$destroy', function() {
                var currentSession = scope.toolWindowCtrl.session;
                var currentContent = elem.children().get(0);
                if (currentContent) {
                    toolWindowDOMCache[currentSession.id] = currentContent;
                }
            });
        }
    };
}]);

