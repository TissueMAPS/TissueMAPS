angular.module('tmaps.shared.auth')
.factory('authInterceptor', ['$q', '$window', function($q, $window) {

    function request(config) {
        config.headers = config.headers || {};
        var token = $window.sessionStorage.token;
        if (angular.isDefined(token)) {
            config.headers.Authorization = 'Bearer ' + token;
        }
        return config;
    }

    function response(response) {
        if (response.status === 401) {
            // handle case when user is not authenticated
        }
        return response || $q.when(response);
    }

    return {
        request: request,
        response: response
    };

}]);
