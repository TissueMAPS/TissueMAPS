// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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
