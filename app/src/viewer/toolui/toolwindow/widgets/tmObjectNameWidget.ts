angular.module('tmaps.ui')
.directive('tmObjectNameWidget', () => {
    var template = 
        '<label>Object type: </label>' +
        '<select ng-model="objectNameWidget.selectedName">' +
          '<option value="{{::t}}" ng-repeat="t in objectNameWidget.mapObjectNames">' +
          '{{::t}}' +
          '</option>' +
        '</select>';
    return {
        restrict: 'E',
        template: template,
        controller: 'ObjectNameWidgetCtrl',
        controllerAs: 'objectNameWidget'
    };
});

class ObjectNameWidgetCtrl {

    static $inject = ['$scope'];

    mapObjectNames: string[] = [];

    constructor(private _$scope: any) {
        this.mapObjectNames = this._$scope.viewer.experiment.mapobjectTypes.map((t) => {
            return t.name;
        });
    }

    get selectedName() {
        return this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType;
    }

    set selectedName(t: string) {
        this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType = t;
    }
}

angular.module('tmaps.ui').
controller('ObjectNameWidgetCtrl', ObjectNameWidgetCtrl);
