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
interface SelectionSettingsControlsScope extends ViewportScope {
    selectionBox: any;
}

/**
 * A controller to manage the control bar in the selections settings
 * section of the sidebar.
 * This controller has access to the selected items (= selections in
 * this case) since it is part of the selection box.
 */
class SelectionControlsCtrl {

    static $inject = ['$scope'];

    selHandler: MapObjectSelectionHandler;
    private _$scope: SelectionSettingsControlsScope;

    constructor($scope: SelectionSettingsControlsScope) {
        this._$scope = $scope;
        this.selHandler = $scope.viewer.mapObjectSelectionHandler;
    }

    clearSelectedSelections() {
        _(this._$scope.selectionBox.getSelectedItems()).each((s) => {
            s.clear();
        });
    }

    deleteSelectedSelections() {
        // Deselect the layer before removing it, otherwise
        // the activeSelectionId may point to a nonexistant selection
        _(this._$scope.selectionBox.getSelectedItems()).each((s) => {
            this.selHandler.removeSelection(s);
        });
    }

}

angular.module('tmaps.ui').controller('SelectionControlsCtrl', SelectionControlsCtrl);

