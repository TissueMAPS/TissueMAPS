angular.module('tmaps.toolwindow')
.directive('tmObjectTypeSelectionWidget', () => {
    var template = 
        '<label>Object type: </label>' +
        '<select ng-model="toolOptions.chosenMapObjectType">' +
          '<option value="{{::t}}" ng-repeat="t in objectTypeSelectionWidget.selHandler.supportedMapObjectTypes">' +
          '{{::t}}' +
          '</option>' +
        '</select>';
    return {
        restrict: 'E',
        template: template,
        controller: 'ObjectTypeSelectionWidgetCtrl',
        controllerAs: 'objectTypeSelectionWidget'
    };
});

class ObjectTypeSelectionWidgetCtrl {

    static $inject = ['tmapsProxy'];

    selHandler: MapObjectSelectionHandler;

    constructor(tmapsProxy: TmapsProxy) {
        this.selHandler = tmapsProxy.appInstance.mapObjectSelectionHandler;
    }
}

angular.module('tmaps.toolwindow').
controller('ObjectTypeSelectionWidgetCtrl', ObjectTypeSelectionWidgetCtrl);
