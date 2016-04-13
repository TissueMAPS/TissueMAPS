interface ClusterScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    objectNameWidget: ObjectNameWidgetCtrl;
}

class ClusterToolCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    nClusters: number = 2;

    constructor(public $scope: ClusterScope,
                public viewer: Viewer) {
        super();
    }

    doCluster() {
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;
        this.sendRequest({
            chosen_object_type: this.$scope.objectNameWidget.selectedName,
            selected_features: selectedFeatures,
            k: this.nClusters
        });
    }
}
