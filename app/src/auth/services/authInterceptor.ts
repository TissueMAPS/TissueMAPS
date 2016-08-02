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
