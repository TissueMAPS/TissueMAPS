interface HeatmapScope extends ToolWindowContentScope {
    featureWidget: FeatureSelectionWidgetCtrl;
    mapobjectTypeWidget: MapobjectTypeWidgetCtrl;
}

class HeatmapToolCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    constructor(public $scope: SVMScope,
                public viewer: Viewer) {
        super();
    }

    submit() {
        // Build the request object
        var selectedFeature = this.$scope.featureWidget.selectedFeatures[0];

        this.sendRequest({
            chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
            selected_feature: selectedFeature
        });
    }
}
