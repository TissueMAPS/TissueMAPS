interface HeatmapScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    objectNameWidget: ObjectNameWidgetCtrl;
}

class HeatmapToolCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    constructor(public $scope: SVMScope,
                public viewer: AppInstance) {
        super();
    }

    submit() {
        // Build the request object
        var selectedFeature = this.$scope.featureWidget.selectedFeatures[0];

        this.sendRequest({
            chosen_object_type: this.$scope.objectNameWidget.selectedName,
            selected_feature: selectedFeature
        });
    }
}
