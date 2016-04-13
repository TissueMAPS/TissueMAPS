class SelectionSettingsCtrl {

    selHandler: MapObjectSelectionHandler;

    static $inject = ['$scope'];

    constructor($scope: ViewportElementScope) {
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
