angular.module('tmaps.ui')
.directive('tmViewport', [function() {
    return {
        restrict: 'EA',
        controller: ['$scope', function($scope) {
            $scope.viewport = $scope.viewer.viewport;
        }],
        controllerAs: 'viewportCtrl',
        bindToController: true,
        templateUrl: '/src/viewer/viewport.html',
        link: function(scope, elem, attr) {
            /**
             * Call the viewport instance of this viewer to create the openlayers map.
             * This will cause the map to be injected into the DOM in the map container
             * DIV. After this the map promise on the viewport will be resolved.
             */
            var htmlElem = elem.find('.map-container').get(0);
            scope.viewer.viewport.renderMap(htmlElem);
        }
    };
}]);
