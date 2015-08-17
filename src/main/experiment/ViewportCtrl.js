/*
 * This controller will be instantiated when the viewport is
 * created. Don't use this directly via ng-controller.
 */
angular.module('tmaps.main.experiment').controller(
    'ViewportCtrl',
        ['$scope', 'appInstance', 'authService', 'appstateService',
            function($scope, appInstance, authService, appstateService) {

    $scope.appInstance = appInstance;

    this.isUserAuthenticated = function() {
        return authService.isAuthenticated();
    };

    this.isUserViewingSnapshot = function() {
        return appstateService.currentState.isSnapshot;
    };

}]);

