// Copyright (C) 2016-2018 University of Zurich.
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
