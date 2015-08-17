angular.module('tmaps.main.auth')
.directive('tmInlineLoginForm', function() {

    return {
        templateUrl: '/templates/main/auth/tm-inline-login-form.html',
        restrict: 'E',
        controller: 'LoginCtrl',
        controllerAs: 'auth'
    };

});
