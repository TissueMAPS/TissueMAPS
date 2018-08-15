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
.factory('authInterceptor', ['$q', '$window', function($q, $window) {

    function request(config) {
        config.headers = config.headers || {};
        var token = $window.sessionStorage.token;
        if (angular.isDefined(token)) {
            config.headers.Authorization = 'JWT ' + token;
        }
        return config;
    }

    function response(resp) {
        if (resp.status === 401) {
            // handle case when user is not authenticated
            console.log('User not authenticated!');
        }
        return resp || $q.when(resp);
    }

    return {
        request: request,
        response: response
    };

}]);
