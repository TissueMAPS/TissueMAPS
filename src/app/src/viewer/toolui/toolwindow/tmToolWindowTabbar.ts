// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
        // TODO: Create a viewport (or maybe better Viewer) directive that sits on the viewport div
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
