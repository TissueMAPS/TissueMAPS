angular.module('tmaps.auth')
.controller('LoginDialogCtrl', ['authService', '$rootScope', '$scope',
            function(authService, $rootScope, $scope) {

    this.form = {
        username: undefined,
        password: undefined
    };

    this.login = function(username, password) {
        authService.login(username, password)
        .then(function(user) {
            // Login was OK, return the current user object to the caller
            $scope.$close(user);
        });
    };
}]);
