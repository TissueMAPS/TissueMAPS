interface VisualLayerSettingsScope extends ng.IScope {
    selectionBox: any;
    visualLayerCtrl: VisualLayerSettingsCtrl;
}

class VisualLayerControlsCtrl {
    static $inject = ['$scope'];

    protected _$scope: VisualLayerSettingsScope;

    constructor($scope) {
        this._$scope = $scope;
    }

    removeSelectedLayers() {
        _(this._$scope.selectionBox.getSelectedItems()).each((layer) => {
            this._$scope.visualLayerCtrl.viewport.removeLayer(layer);
        });
    };

}

angular.module('tmaps.ui').controller('VisualLayerControlsCtrl', VisualLayerControlsCtrl);
