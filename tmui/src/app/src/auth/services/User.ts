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
// TODO: Add additional information such as first name, last name, etc.
.factory('User', ['USER_ROLES', function(USER_ROLES) {
    function User(id, name, roles) {
        this.id = id;
        this.name = name;
        this.roles = roles;
    }

    User.prototype.isAdmin = function() {
        return _(this.roles).contains(USER_ROLES.admin);
    };

    return User;
}]);
