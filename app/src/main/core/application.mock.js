angular.module('tmaps.mock.core')
.factory('application', ['$q', function($q) {

    var application = {};

    angular.extend(application, jasmine.createSpyObj('application', [
        'hideViewport',
        'showViewport',
        'removeInstance',
        'destroyAllInstances',
        'setActiveInstanceByNumber',
        'setActiveInstance',
        'getInstanceByExpName',
        'getInstanceById',
        'isActiveInstanceByIndex',
        'isActiveInstanceById',
        'addExperiment',
        'getToolById',
        'initFromBlueprint'
    ]));

    application.toBlueprint = jasmine.createSpy('toBlueprint').and.callFake(function() {
        var fakeBlueprintPromise = $q.when({});
        return fakeBlueprintPromise;
    });

    return application;
}]);
