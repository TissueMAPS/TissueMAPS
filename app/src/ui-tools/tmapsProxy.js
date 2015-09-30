angular.module('tmaps.tools')
.service('tmapsProxy', ['$window', function($window) {

    if (angular.isDefined($window.init)) {
        this.application = $window.init.tmapsProxy.application;
        this.viewport = $window.init.tmapsProxy.viewport;
        // TODO: Include the Viewport scope so that the pubsub
        // system isn't automatically global.
        this.$rootScope = $window.init.tmapsProxy.$rootScope;
    } else {
        console.log('No tmaps object on the global scope!');
    }

}]);
