interface ClusterScope extends ToolWindowScope {
    // featureWidget: FeatureSelectionWidgetCtrl;
}

class ClusterCtrl {
    static $inject = ['$scope'];

    nClusters: number = 2;

    constructor(public $scope: ClusterScope) {
    }

    sendRequest() {
        // var selectedFeatures =
        //     _(this._$scope.featureWidget.selectedFeatures).pluck('name');
        // var payload = {
        //     chosen_object_type: this._$scope.toolOptions.chosenMapObjectType,
        //     selected_features: selectedFeatures,
        //     k: this.nClusters
        // };
        // this._tool.sendRequest(payload).then((response) => {
        //     console.log(response);
        // });
    }
}

angular.module('tmaps.ui')
.controller('ClusterCtrl', ClusterCtrl);
