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
class SelectionSettingsCtrl {

    selHandler: MapObjectSelectionHandler;

    static $inject = ['$scope'];

    constructor($scope: ViewportScope) {
        this.selHandler = $scope.viewer.mapObjectSelectionHandler;
    }

    isActiveSelection(sel: MapObjectSelection) {
        return this.selHandler.activeSelection === sel;
    }

    toggleActiveSelection(sel: MapObjectSelection) {
        if (this.selHandler.activeSelection === sel) {
            this.selHandler.activeSelection = null;
        } else {
            this.selHandler.activeSelection = sel;
        }
    }

    addSelection() {
        this.selHandler.addNewSelection(this.selHandler.activeMapObjectType);
    }

}

angular.module('tmaps.ui') .controller('SelectionSettingsCtrl', SelectionSettingsCtrl);

class SelectionTabCtrl {
    static $inject = ['$scope'];

    selection: MapObjectSelection;
    inRenamingMode: boolean = false;

    constructor(private _$scope: any) {
        this.selection = _$scope.sel;
    }

    toggleRenamingMode() {
        this.inRenamingMode = !this.inRenamingMode;
    }
}

angular.module('tmaps.ui') .controller('SelectionTabCtrl', SelectionTabCtrl);
