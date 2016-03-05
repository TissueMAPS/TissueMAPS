interface ClusterScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    objectNameWidget: ObjectNameWidgetCtrl;
}

class ClusterToolCtrl {
    static $inject = ['$scope', 'viewer', 'session'];

    nClusters: number = 2;

    constructor(public $scope: ClusterScope,
                public viewer: AppInstance,
                public session: ClusterToolSession) {
    }

    sendRequest() {
        console.log('asdf');
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;
        var payload = {
            chosen_object_type: this.$scope.objectNameWidget.selectedName,
            selected_features: selectedFeatures,
            k: this.nClusters
        };
        this.session.sendRequest(this.viewer.experiment, payload);
    }
}
