interface SVMScope extends ToolContentScope {
    svm: SVMCtrl;
    classSelectionWidget: ClassSelectionWidgetCtrl;
    featureWidget: FeatureSelectionWidgetCtrl;
}

class SVMCtrl {
    static $inject = ['$scope', 'tmapsProxy'];

    private _$scope: SVMScope;
    private _tool: SVMTool;

    constructor($scope: SVMScope, tmapsProxy: TmapsProxy) {
        this._$scope = $scope;
        this._tool = tmapsProxy.tool;
    }

    sendRequest() {
        // Build the request object
        var trainingClasses = [];
        this._$scope.classSelectionWidget.classes.forEach((cls) => {
            trainingClasses.push({
                name: cls.name,
                object_ids: _(cls.selection.mapObjects).pluck('id'),
                color: cls.selection.color.toHex()
            });
        });
        var selectedFeatures =
            _(this._$scope.featureWidget.selectedFeatures).pluck('name');
        var payload = {
            chosen_object_type: this._$scope.toolOptions.chosenMapObjectType,
            training_classes: trainingClasses,
            selected_features: selectedFeatures
        };
        this._tool.sendRequest(payload).then(function(response) {
            console.log(response);
        });
    }
}

angular.module('tmaps.toolwindow').controller('SVMCtrl', SVMCtrl);
