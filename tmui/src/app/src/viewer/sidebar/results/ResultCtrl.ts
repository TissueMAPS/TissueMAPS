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
    private _origName: string;

    inRenamingMode: boolean = false;

    get opacityInput() {
        return this._opacityInput;
    }

    set opacityInput(v: number) {
        this._opacityInput = v;
        this.result.layers.forEach((l) => {
            l.opacity = v / 100;
        })
    }

    toggleRenamingMode() {
        this.inRenamingMode = !this.inRenamingMode;
    }

    changeName() {
        var dao = new ToolResultDAO(this.result.viewer.experiment.id);
        var newName = this.result.name.replace(/[^-A-Z0-9]+/ig, "_");
        dao.update(this.result.id, {
            name: newName
        }).then(() => {
            // Replace all special characters by underscore
            this.result.name = newName;
        }, () => {
            this.result.name = this._origName;
        });
    }

    static $inject = ['$scope'];

    constructor($scope: any, private _$stateParams) {
        this.result = $scope.result;
        this.opacityInput = this.result.layers[0].opacity * 100;
        this._origName = this.result.name;
    }
}

angular.module('tmaps.ui').controller('ResultCtrl', ResultCtrl);
