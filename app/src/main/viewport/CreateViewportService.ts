class CreateViewportService {

    static $inject = ['$http', 'openlayers', '$q', '$controller', '$compile', '$rootScope'];

    constructor(private $http: ng.IHttpService,
                private openlayers,
                private $q: ng.IQService,
                private $controller: ng.IControllerService,
                private $compile: ng.ICompileService,
                private $rootScope: ng.IRootScopeService) {}

    private getTemplate(templateUrl): ng.IPromise<string> {
        var deferred = this.$q.defer();
        this.$http({method: 'GET', url: templateUrl, cache: true})
        .then(function(result) {
            deferred.resolve(result.data);
        })
        .catch(function(error) {
            deferred.reject(error);
        });
        return deferred.promise;
    }

    private createViewportSync(appInstance: AppInstance,
                               appendToId: string,
                               templateString: string): Viewport {
        var newScope = <ViewportScope> this.$rootScope.$new();
        newScope.appInstance = appInstance;
        var ctrl = this.$controller('ViewportCtrl', {
            '$scope': newScope,
            'appInstance': appInstance
        });
        newScope.viewport = ctrl;

        // The divs have to be shown and hidden manually since ngShow
        // doesn't quite work correctly when doing it this way.
        var elem = angular.element(templateString);

        // Compile the element (expand directives)
        var linkFunc = this.$compile(elem);
        // Link to scope
        var viewportElem = linkFunc(newScope);

        // Append to viewports
        $('#' + appendToId).append(viewportElem);
        // Append map after the element has been added to the DOM.
        // Otherwise the viewport size calculation of openlayers gets
        // messed up.
        var map = new ol.Map({
            layers: [],
            controls: [],
            renderer: 'webgl',
            target: viewportElem.find('.map-container')[0],
            logo: false
        });

        return {
            element: viewportElem,
            scope: newScope,
            controller: ctrl,
            map: map
        };
    }

    createViewport(appInstance, appendToId, templateUrl): ng.IPromise<Viewport> {
        var deferred = this.$q.defer();
        this.getTemplate(templateUrl).then((templateString) => {
            var viewportObj = this.createViewportSync(appInstance, appendToId, templateString);
            deferred.resolve(viewportObj);
        });
        return deferred.promise;
    }
}

/**
 * Create a viewport and append it to a given div.
 * This function returns the controller, map, scope, element object
 * inside a promise.
 * The reason this wasn't done via directives is that the whole
 * process got somewhat complicated when the map canvas got resized
 * etc. This approach is less angulary but it works.
 */
angular.module('tmaps.main.viewport').service('createViewportService', CreateViewportService);
