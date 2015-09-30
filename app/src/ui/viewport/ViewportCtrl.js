/*
 * This controller will be instantiated when the viewport is
 * created. Don't use this directly via ng-controller.
 */
angular.module('tmaps.core').controller(
    'ViewportCtrl',
        ['$scope', 'viewport', 'authService', 'appstateService',
            function($scope, viewport, authService, appstateService) {

    $scope.viewport = viewport;

    this.isUserAuthenticated = function() {
        return authService.isAuthenticated();
    };

    this.isUserViewingSnapshot = function() {
        return appstateService.hasCurrentState() && appstateService.getCurrentState().isSnapshot;
    };

}]);

