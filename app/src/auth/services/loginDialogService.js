angular.module('tmaps.auth')
.service('loginDialogService', ['$modal', '$rootScope', function($modal, $rootScope) {

    this.showDialog = function() {

        var instance = $modal.open({
            templateUrl: '/templates/main/auth/login-dialog.html',
            controller: 'LoginDialogCtrl',
            controllerAs: 'login'
        });

        return instance.result;

    };

}]);
