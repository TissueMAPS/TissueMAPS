class ResultsControlsCtrl {
    static $inject = ['$scope'];

    constructor(private _$scope: ResultsSettingsScope) {}

    removeSelectedResults() {
        var $scope = this._$scope;
        $scope.selectionBox.getSelectedItems().forEach((res) => {
            $scope.resultsSettingsCtrl.viewer.deleteSavedResult(res);
        });
    };

}

angular.module('tmaps.ui').controller('ResultsControlsCtrl', ResultsControlsCtrl);
