interface ToolWindowTabScope {
    open: boolean;
    session: ToolSession;
}

angular.module('tmaps.toolwindow')
.directive('tmToolWindowTab', () => {
    return {
        require: '^ToolWindowTabbar',
        scope: {
            toolSession: '='
        },
        link: (scope: ToolWindowTabScope, element, attrs, tabbarCtrl) => {
            tabbarCtrl.addTab(scope);

            element.bind('click', () => {
                tabbarCtrl.select(scope);
                // angular.element(document.getElementById('space-for-buttons')).append($compile("<div><button class='btn btn-default' data-alert="+scope.count+">Show alert #"+scope.count+"</button></div>")(scope));
            });
        },
        template: '<li>{{ toolSession.tool.name }}</li>'
    };
})
.directive('tmToolWindowTabbar', ['$compile', '$rootScope', ($compile, $rootScope) => {
    return {
        // TODO: Needs access to the viewport scope
        // TODO: Create a viewport (or maybe better AppInstance) directive that sits on the viewport div
        // The ViewportCtrl should then have the $scope directly on in.
        // In this way all directives can just "require: '^^viewport"
        // and get a link to the viewport scope that they can use to broadcast stuff.
        template: 'sess in toolSessions ng-click="select(sess)"',
        controller: ['$scope', ($scope) => {
            var tabs: ToolWindowTabScope[] = [];

            this.addTab = (tab) => {
                tabs.push(tab);
            };

            this.select = (tab) => {
                _(tabs).each((t) => {
                    t.open = false;
                });
                tab.open = true;
                // TODO: Show window
                // $rootScope.$broadcast('showToolWindow', t.session);
            }
        }]
    };
}])
.directive('tmToolWindowContainer', [() => {}]);
