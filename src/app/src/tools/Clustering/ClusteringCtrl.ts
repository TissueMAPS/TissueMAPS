interface ClusterScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    mapobjectTypeWidget: MapobjectTypeWidgetCtrl;
}

class ClusteringCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    nClusters: number = 2;
    algorithm: string = 'kmeans';

    constructor(public $scope: ClusterScope,
                public viewer: Viewer) {
        super();
    }

    doCluster() {
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;
        this.sendRequest({
            chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
            selected_features: selectedFeatures,
            k: this.nClusters,
            method: this.algorithm
        });
    }
}
