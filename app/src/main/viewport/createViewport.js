/**
 * Create a viewport and append it to a given div.
 * This function returns the controller, map, scope, element object
 * inside a promise.
 * The reason this wasn't done via directives is that the whole
 * process got somewhat complicated when the map canvas got resized
 * etc. This approach is less angulary but it works.
 */
angular.module('tmaps.main.viewport').factory('createViewport',
     ['$http', 'openlayers', '$q', '$controller', '$compile', '$rootScope',
         function($http, ol, $q, $controller, $compile, $rootScope) {

    function getTemplate(templateUrl) {
        var deferred = $q.defer();
        $http({method: 'GET', url: templateUrl, cache: true})
        .then(function(result) {
            deferred.resolve(result.data);
        })
        .catch(function(error) {
            deferred.reject(error);
        });
        return deferred.promise;
    }

    function createViewportSync(appInstance, appendToId, templateString) {
        var viewportId = 'instance-viewport-' + appInstance.id;
        var newScope = $rootScope.$new();
        newScope.appInstance = appInstance;
        var ctrl = $controller('ViewportCtrl', {
            '$scope': newScope,
            'appInstance': appInstance
        });
        newScope.viewport = ctrl;

        // The divs have to be shown and hidden manually since ngShow
        // doesn't quite work correctly when doing it this way.
        var elem = angular.element(templateString);

        // Compile the element (expand directives)
        var linkFunc = $compile(elem);
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

        window.map = map;

        return {
            element: viewportElem,
            scope: newScope,
            controller: ctrl,
            map: map
        };
    }

    function createViewport(appInstance, appendToId, templateUrl) {
        var deferred = $q.defer();
        getTemplate(templateUrl).then(function(templateString) {
            var viewportObj = createViewportSync(appInstance, appendToId, templateString);
            deferred.resolve(viewportObj);
        });
        return deferred.promise;
    }

    return createViewport;
}]);

