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
.factory('jwtUtil', ['$window', function($window) {

    function decodeToken(token) {
        var parts = token.split('.');
        var headerBase64 = parts[0];
        var payloadBase64 = parts[1];

        function decode(partBase64) {
            partBase64 = partBase64.replace('-', '+').replace('_', '/');
            return JSON.parse($window.atob(partBase64));
        }

        return {
            header: decode(headerBase64),
            payload: decode(payloadBase64)
        };
    }

    function isTokenExpired(token) {
        if (!token || token === '') {
            return true;
        } else {
            var decoded = decodeToken(token);
            var exp = decoded.payload.exp;
            var d = new Date(0);
            d.setUTCSeconds(exp);
            return !(d.valueOf() > new Date().valueOf());
        }
    }

    return {
        decodeToken: decodeToken,
        isTokenExpired: isTokenExpired
    };
}]);
