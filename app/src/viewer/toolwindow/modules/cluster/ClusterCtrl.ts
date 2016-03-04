interface ClusterScope extends ToolWindowScope {
    // featureWidget: FeatureSelectionWidgetCtrl;
}

class ClusterCtrl {
    static $inject = ['$scope', 'viewer', 'tool'];

    nClusters: number = 2;

    constructor(public $scope: ClusterScope,
                public viewer: AppInstance,
                public tool: ClusterTool) {
        console.log(viewer);
        console.log(tool);
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

// angular.module('tmaps.ui').controller('ClusterCtrl', ClusterCtrl);
