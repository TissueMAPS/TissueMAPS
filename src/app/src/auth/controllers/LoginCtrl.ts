angular.module('tmaps.auth')
.controller('LoginCtrl', ['$scope', '$rootScope', 'authService', '$state',
            function($scope, $rootScope, authService, $state) {

    var self = this;

    this.form = {
        username: undefined,
        password: undefined
    };

    this.isAlreadyLoggedIn = function() {
        return authService.isAuthenticated();
    };

    this.login = function() {
        authService.login(self.form.username, self.form.password)
        .then(function(user) {
            $state.go('userpanel');
        },
        function(err) {
            console.log(err);
        });
    };
}]);
