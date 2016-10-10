angular.module('tmaps.ui')
.directive('tmMapobjectTypeWidget', () => {
    var template = 
        '<label>Object type: </label>' +
        '<select ng-model="mapobjectTypeWidget.selectedType" ng-options="t for t in mapobjectTypeWidget.mapobjectTypeNames">' +
        '</select>';
    return {
        restrict: 'E',
        template: template,
        controller: 'MapobjectTypeWidgetCtrl',
        controllerAs: 'mapobjectTypeWidget',
        scope: true
    };
});

class MapobjectTypeWidgetCtrl {

    static $inject = ['$scope'];

    mapobjectTypeNames: string[] = [];

    constructor(private _$scope: any) {
        this._$scope.$parent['mapobjectTypeWidget'] = this;
        this.mapobjectTypeNames = this._$scope.viewer.mapobjectTypes.map((t) => {
            return t.name;
        });
    }

    get selectedType() {
        return this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType;
    }

    set selectedType(t: string) {
        this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType = t;
    }
}

angular.module('tmaps.ui').
controller('MapobjectTypeWidgetCtrl', MapobjectTypeWidgetCtrl);
