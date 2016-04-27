interface FeatureTab {
    selected: boolean;
    name: string;
}

class FeatureSelectionWidgetCtrl {

    name: string;
    maxSelections: number;
    nSelected: number = 0;
    featureQuery: { name: string; } = {
        name: undefined
    };
    selectedObjectName: string;

    private _featureTabsByName: {[objName: string]: FeatureTab[];} = {};

    static $inject = ['$scope'];

    constructor(public $scope: ToolWindowContentScope) {
        this.name = this.name === undefined ? 'featureWidget' : this.name;
        this.maxSelections = this.maxSelections === undefined ? Infinity: this.maxSelections;

        this.$scope.$parent[this.name] = this;

        var parentScope = <ToolWindowContentScope>this.$scope.$parent;
        var experiment = parentScope.viewer.experiment;
        experiment.mapobjectTypes.forEach((type) => {
            console.log(type.features);
            var featureTabs = type.features.map((f) => {
                return {
                    name: f.name,
                    selected: false
                };
            });
            this._featureTabsByName[type.name] = featureTabs;
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
        var wasSelected = tab.selected;

        if (this.nSelected < this.maxSelections) {
            tab.selected = true;
            if (!wasSelected) {
                this.nSelected += 1;
            }
        } else {
            // Check if the user chose to limit the number of selected features to one.
            // In this case a new selection should automatically deselect all other features
            // s.t. it is not required to deselect the other feature first.
            var isSingleSelection = this.maxSelections == 1;
            if (isSingleSelection) {
                this.featureTabsForChosenName.forEach((tab) => {
                    this.deselectFeature(tab);
                });
                tab.selected = true;
                if (!wasSelected) {
                    this.nSelected += 1;
                }
            } else {
                console.log('Can\'t select any more features, deselect some!');
            }
        }
    }

    deselectFeature(tab) {
        var wasSelected = tab.selected;
        tab.selected = false;
        if (wasSelected) {
            this.nSelected -= 1;
        }
    }

    get featureTabsForChosenName() {
        return this._featureTabsByName[this.selectedObjectName];
    }

    get selectedFeatures() {
        return _.chain(this.featureTabsForChosenName)
        .filter((t) => {
            return t.selected;
        }).map((f) => {
            return f.name;
        }).value();
    }

    setAll(isSelected: boolean) {
        for (var t in this._featureTabsByName) {
            this._featureTabsByName[t].forEach((tab) => {
                if (isSelected) {
                    this.selectFeature(tab);
                } else {
                    this.deselectFeature(tab);
                }
            });
        }
    }
}

angular.module('tmaps.ui').controller('FeatureSelectionWidgetCtrl', FeatureSelectionWidgetCtrl);

angular.module('tmaps.ui')
/**
 * A directive with which features can be selected.
 *
 * Example usage:
 *
 *  <tm-feature-selection-widget></tm-feature-selection-widget>
 */
.directive('tmFeatureSelectionWidget', function() {
    return {
        restrict: 'E',
        templateUrl: '/src/viewer/toolui/toolwindow/widgets/tm-feature-selection-widget.html',
        controller: 'FeatureSelectionWidgetCtrl',
        controllerAs: 'featureWidget',
        bindToController: true,
        scope: {
            name: '@name',
            maxSelections: '@maxSelections',
            selectedObjectName: '='
        }
    };
});
