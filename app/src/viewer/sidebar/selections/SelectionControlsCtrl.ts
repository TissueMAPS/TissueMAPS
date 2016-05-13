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

