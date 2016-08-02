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
