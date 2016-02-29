interface ClusterScope extends ToolContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
}

class ClusterCtrl {
    static $inject = ['$scope', 'tmapsProxy'];

    nClusters: number = 2;

    private _$scope: ClusterScope;
    private _tool: ClusterTool;

    constructor($scope: ClusterScope, tmapsProxy: TmapsProxy) {
        this._$scope = $scope;
        this._tool = tmapsProxy.tool;
    }

    sendRequest() {
        var selectedFeatures =
            _(this._$scope.featureWidget.selectedFeatures).pluck('name');
        var payload = {
            chosen_object_type: this._$scope.toolOptions.chosenMapObjectType,
            selected_features: selectedFeatures,
            k: this.nClusters
        };
        this._tool.sendRequest(payload).then((response) => {
            console.log(response);
        });
    }
}

angular.module('tmaps.toolwindow')
.controller('ClusterCtrl', ClusterCtrl);
