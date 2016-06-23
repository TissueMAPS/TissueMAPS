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
