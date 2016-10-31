angular.module('tmaps.ui')
.factory('errorInterceptor', ['$injector', function($injector) {

    function response(resp) {
        // Inject directly because of circular dependency hell
        var $uibModal = $injector.get('$uibModal');
        var $q = $injector.get('$q');
        // Check if the response was a flask-generated custom JSON
        // error response.
        if (resp.data.error) {
            // The error payload should contain a message property that describes this error.
            var errorMessage =
                resp.data.message || resp.data.type || ('Error ' + resp.data.status_code);
            var instance = $uibModal.open({
                template: errorMessage
            });
        }
        return resp;
        return resp || $q.when(resp);
    }

    return {
        response: response
    };

}]);
