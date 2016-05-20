interface RandomForestScope extends ToolWindowContentScope {
    randomForest: RandomForestCtrl;
    featureWidget: FeatureSelectionWidgetCtrl;
    mapobjectTypeWidget: MapobjectTypeWidgetCtrl;
    classSelectionWidget: ClassSelectionWidgetCtrl;
}

class RandomForestCtrl extends ToolCtrl {
    static $inject = ['$scope', 'viewer'];

    constructor(public $scope: RandomForestScope,
                public viewer: Viewer) {
        super();
    }

    doClassify() {
        // Build the request object
        var selectedFeatures = this.$scope.featureWidget.selectedFeatures;

        var trainingClasses = [];
        this.$scope.classSelectionWidget.classes.forEach((cls) => {
            trainingClasses.push({
                name: cls.name,
                object_ids: cls.mapobjectIds,
                color: cls.color.toHex()
            });
        });

        this.sendRequest({
            chosen_object_type: this.$scope.mapobjectTypeWidget.selectedType,
            selected_features: selectedFeatures,
            training_classes: trainingClasses
        });
    }
}
