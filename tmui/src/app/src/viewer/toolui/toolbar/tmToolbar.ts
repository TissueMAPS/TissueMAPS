// Copyright (C) 2016-2018 University of Zurich.
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
interface ToolbarScope extends ToolUIScope {
    toolbarCtrl: ToolbarCtrl;
}

/**
 * ToolbarCtrl is a controller that manages the list of buttons with which
 * different tools may be accessed. This controller concerns itself with
 * what happens when such a button is pressed.
 */
class ToolbarCtrl {
    static $inject = ['$scope', 'application', 'authService'];

    tools: Tool[] = [];

    constructor(public $scope: ToolbarScope,
                private application: Application,
                private authService) {
        // Add the tools as soon as they are ready
        this.$scope.viewer.tools.then((tools) => {
            this.tools = tools;
        });
    }

    /**
     * This function is called when the Tool's button is pressed.
     */
    clickToolTab(tool: Tool) {
        this.$scope.toolUICtrl.toggleToolWindow(tool);
    }
}
angular.module('tmaps.ui').controller('ToolbarCtrl', ToolbarCtrl);
angular.module('tmaps.ui')
.directive('tmToolbar', function() {
    return {
        restrict: 'E',
        controller: 'ToolbarCtrl',
        controllerAs: 'toolbarCtrl',
        templateUrl: '/src/viewer/toolui/toolbar/tm-toolbar.html'
    };
});
