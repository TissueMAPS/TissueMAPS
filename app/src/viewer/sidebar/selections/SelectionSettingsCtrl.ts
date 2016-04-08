class SelectionSettingsCtrl {

    selHandler: MapObjectSelectionHandler;

    static $inject = ['$scope'];

    constructor($scope: ViewportElementScope) {
        this.selHandler = $scope.appInstance.mapObjectSelectionHandler;
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
