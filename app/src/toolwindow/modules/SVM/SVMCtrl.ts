interface SVMScope extends ng.IScope {
    svm: SVMCtrl;
    selWidget: ClassSelectionWidgetCtrl;
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
        this._$scope.selWidget.classes.forEach((cls) => {
            trainingClasses.push({
                name: cls.name,
                object_ids: _(cls.selection.mapObjects).pluck('id')
            });
        });
        // TODO:
        // var selectedFeatures = this._$scope.featWidget.selectedFeatures;
        var selectedFeatures = {};
        var payload = {
            training_classes: trainingClasses,
            selected_features: selectedFeatures
        };
        this._tool.sendRequest(payload).then(function(response) {
            console.log(response);
        });
    }
}

angular.module('tmaps.toolwindow').controller('SVMCtrl', SVMCtrl);
