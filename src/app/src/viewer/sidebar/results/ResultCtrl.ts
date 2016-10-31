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
class ResultCtrl {
    result: ToolResult;

    private _opacityInput: number;

    get opacityInput() {
        return this._opacityInput;
    }

    set opacityInput(v: number) {
        this._opacityInput = v;
        this.result.layer.opacity = v / 100;
    }

    static $inject = ['$scope'];

    constructor($scope: any) {
        this.result = $scope.result;
        this.opacityInput = this.result.layer.opacity * 100;
    }
}

angular.module('tmaps.ui').controller('ResultCtrl', ResultCtrl);
