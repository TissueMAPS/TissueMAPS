type FeatureTab = {
    selected: boolean;
    name: string;
}

class FeatureSelectionWidgetCtrl {

    static $inject = ['$http', 'tmapsProxy', '$scope'];

    featureQuery: { name: string; } = {
        name: undefined
    };
    toolOptions: ToolOptions;

    private _featureTabsByType: {[objType: string]: FeatureTab[];} = {};
    private _selHandler: MapObjectSelectionHandler;

    constructor($http: ng.IHttpService,
                tmapsProxy: TmapsProxy,
                $scope: ToolContentScope) {

        this._selHandler = tmapsProxy.appInstance.mapObjectSelectionHandler;
        this.toolOptions = $scope.toolOptions;
        var featManager = tmapsProxy.appInstance.featureManager;

        this._selHandler.supportedMapObjectTypes.forEach((t) => {
            // Init as empty array s.t. angular will just display
            // no features when promise isn't resolved.
            this._featureTabsByType[t] = [];
            featManager.getFeaturesForType(t).then((feats) => {
                // Create a tab object for each feature.
                // Tabs are initially not selected.
                this._featureTabsByType[t] = feats.map((f) => {
                    return {
                        name: f.name,
                        selected: false
                    };
                });
            });
        });
        window['$scope'] = $scope;
    }

    get featureTabsForChosenType() {
        return this._featureTabsByType[this.toolOptions.chosenMapObjectType];
    }

    get selectedFeatures() {
        var feats = [];
        this.featureTabsForChosenType.map((tab) => {
            if (tab.selected) {
                feats.push({
                    name: tab.name
                });
            }
        });
        return feats;
    }

    setAll(isSelected: boolean) {
        for (var t in this._featureTabsByType) {
            this._featureTabsByType[t].forEach((tab) => {
                tab.selected = isSelected;
            });
        }
    }

}

angular.module('tmaps.toolwindow').controller('FeatureSelectionWidgetCtrl', FeatureSelectionWidgetCtrl);

        //     console.log(tmapsProxy);
        //     tmapsProxy.appInstance.experiment.features
        //     .then(function(feats) {
        //         self.features = feats;
        //         $scope.$digest();
        //     });

        //     this.toggleSelection = function(feat) {

        //         if (self.singleSelection) {
        //             _(self.features).each(function(f) {
        //                 if (f != feat) {
        //                     f.selected = false;
        //                 }
        //             });
        //         }
        //         feat.selected = !feat.selected;

        //         // Extract only those values that are of interest to
        //         // the user of this directive.
        //         // Also, we need to recalculate the original values to which
        //         // the slider range corresponds.
        //         var selectedFeatures = _.chain(self.features)
        //              .filter(function(f) {
        //                 return f.selected;
        //               })
        //              .map(function(f) {
        //                 var feat = { name: f.name };
        //                 if (self.showRange) {
        //                     feat.range = [f.normRange[0] / f.fac, f.normRange[1] / f.fac];
        //                 }
        //                 return feat;
        //               })
        //              .value();

        //         self.onChange({
        //             selectedFeatures: selectedFeatures
        //         });
        //     };

        //     this.setAll = function(val) {
        //         _(self.features).each(function(f) {
        //             f.selected  = val;
        //         });
        //     };
        // }],
