angular.module('tmaps.auth')
.controller('LoginCtrl', ['$scope', '$rootScope', 'authService',
            function($scope, $rootScope, authService) {

    var self = this;

    this.form = {
        username: undefined,
        password: undefined
    };

    this.isAlreadyLoggedIn = function() {
        return authService.isAuthenticated();
    };

    this.login = function() {
        authService.login(self.form.username, self.form.password);
    };
}]);
