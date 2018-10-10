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
