class ResultsControlsCtrl {
    static $inject = ['$scope'];

    protected _$scope: ResultsSettingsScope;

    constructor($scope) {
        this._$scope = $scope;
    }

    removeSelectedResults() {
        _(this._$scope.selectionBox.getSelectedItems()).each((res) => {
            this._$scope.resultSettingsCtrl.removeResult(res);
        });
    };

}

angular.module('tmaps.ui').controller('ResultsControlsCtrl', ResultsControlsCtrl);
