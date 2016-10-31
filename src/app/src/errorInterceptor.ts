angular.module('tmaps.ui')
.factory('errorInterceptor', ['$injector', function($injector) {

    function responseError(resp) {
        // Inject directly because of circular dependency hell
        var $uibModal = $injector.get('$uibModal');
        var $q = $injector.get('$q');
        // Check if the response was a flask-generated custom JSON
        // error response.
        if (resp.data.error) {
            var error = resp.data.error;
            // The error payload should contain a message property that describes this error.
            var errorMessage =
                error.message || error.type || ('Error ' + error.status_code);
            var instance = $uibModal.open({
                templateUrl: '/src/error.html',
                resolve: {
                    errorMessage: function() {
                        return errorMessage;
                    }
                },
                controller: ['$scope', 'errorMessage', function($scope, errorMessage) {
                    $scope.errorMessage = errorMessage;
                }]
            });
        }
        return resp || $q.when(resp);
    }

    return {
        responseError: responseError
    };

}]);
