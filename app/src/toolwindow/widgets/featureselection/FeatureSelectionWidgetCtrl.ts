type FeatureTab = {
    selected: boolean;
    mapObjectType: MapObjectType;
    name: string;
}

class FeatureSelectionWidgetCtrl {

    static $inject = ['$http', 'tmapsProxy', '$scope'];

    name: string;
    maxSelections: number = Infinity;
    nSelected: number = 0;
    featureQuery: { name: string; } = {
        name: undefined
    };
    toolOptions: ToolOptions;

    private _featureTabsByType: {[objType: string]: FeatureTab[];} = {};
    private _selHandler: MapObjectSelectionHandler;
    private _parentScope: ToolContentScope;

    constructor($http: ng.IHttpService,
                tmapsProxy: TmapsProxy,
                $scope: ToolContentScope) {

        // Default
        if (this.name === undefined) {
            this.name = 'featureWidget';
        }
        $scope.$parent[this.name] = this;

        this._parentScope = <ToolContentScope>$scope.$parent;
        this._selHandler = tmapsProxy.appInstance.mapObjectSelectionHandler;
        this.toolOptions = this._parentScope.toolOptions;
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
                        mapObjectType: t,
                        selected: false
                    };
                });
            });
        });
    }

    toggleFeatureSelection(tab: FeatureTab) {
        if (tab.selected) {
            this.deselectFeature(tab);
        } else {
            this.selectFeature(tab);
        }
    }

    selectFeature(tab) {
        if (this.nSelected < this.maxSelections) {
            var wasSelected = tab.selected;
            tab.selected = true;
            if (!wasSelected) {
                this._parentScope.$broadcast('featureSelected', tab, this);
            }
            this.nSelected += 1;
        } else {
            console.log('Can\'t select any more features, deselect some!');
        }
    }

    deselectFeature(tab) {
        var wasSelected = tab.selected;
        tab.selected = false;
        if (wasSelected) {
            this._parentScope.$broadcast('featureDeselected', tab, this);
        }
        this.nSelected -= 1;
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
                if (isSelected) {
                    this.selectFeature(tab);
                } else {
                    this.deselectFeature(tab);
                }
            });
        }
    }
}

angular.module('tmaps.toolwindow').controller('FeatureSelectionWidgetCtrl', FeatureSelectionWidgetCtrl);
