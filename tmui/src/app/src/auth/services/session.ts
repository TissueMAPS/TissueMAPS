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
.service('session',
         ['$window', 'jwtUtil', 'User', '$interval',
            function($window, jwtUtil, User, $interval) {

    var user = null;

    var tokenValid = false;

    /**
     * Start to check the token every `milliseconds` for invaliditity.
     * This function will only set tokenValid to false, never to true!
     */
    var intervalPromise = undefined;

    function startCheckingToken(milliseconds) {
        function checkIfTokenIsValid() {
            var token = $window.sessionStorage.token;
            var tokenExists = !_.isUndefined(token);

            if (!tokenExists) {
                tokenValid = false;
            } else {
                var tokenExpired = jwtUtil.isTokenExpired(token);
                var userLoggedIn = !!user;

                if (tokenExpired) { console.log('Token expired'); }

                if (tokenExpired || !userLoggedIn) {
                    tokenValid = false;
                }
            }
        }

        $interval(checkIfTokenIsValid, milliseconds);
    }

    function stopCheckingToken() {
        $interval.cancel(intervalPromise);
    }

    function setTokenValid() {
        tokenValid = true;
        startCheckingToken(1000);
    }

    function setTokenInvalid() {
        stopCheckingToken();
        tokenValid = false;
    }

    /**
     * Check if there is still a token in the sessionStorage.
     * Maybe the page was reloaded but the token is still there.
     */
    var token = $window.sessionStorage.token;
    if (angular.isDefined(token) && !jwtUtil.isTokenExpired(token)) {
        console.log('Restoring session from existing token...');
        var tokenDecoded = jwtUtil.decodeToken(token);
        var payload = tokenDecoded.payload;
        user = new User(payload.uid, payload.uname, payload.uroles);

        setTokenValid();
    }

    this.create = function(token) {
        var tokenDec = jwtUtil.decodeToken(token);
        var payload = tokenDec.payload;
        var header = tokenDec.header;
        user = new User(payload.uid, payload.uname, payload.uroles);
        $window.sessionStorage.token = token;

        setTokenValid();

        return user;
    };

    this.destroy = function() {
        delete $window.sessionStorage.token;
        user = null;

        setTokenInvalid();
    };

    this.getUser = function() {
        return user;
    };

    this.isAuth = function() {
        return tokenValid;
    };

}]);
