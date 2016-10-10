angular.module('tmaps.auth')
.directive('tmInlineLoginForm', function() {

    var template =
        '<form class="tm-inline-login-form navbar-form navbar-right"' +
              'ng-submit="auth.login()"' +
              'ng-hide="auth.isAlreadyLoggedIn()">' +
          '<div class="form-group">' +
            '<input type="text" placeholder="username" class="form-control"' +
                   'ng-model="auth.form.username">' +
          '</div>' +
          '<div class="form-group">' +
            '<input type="password" placeholder="password" class="form-control"' +
                   'ng-model="auth.form.password">' +
          '</div>' +
          '<button type="submit" class="btn btn-success">Sign in</button>' +
        '</form>';

    return {
        template: template,
        restrict: 'E',
        controller: 'LoginCtrl',
        controllerAs: 'auth'
    };

});
