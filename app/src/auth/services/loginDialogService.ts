angular.module('tmaps.auth')
.service('loginDialogService', ['$uibModal', '$rootScope', function($uibModal, $rootScope) {

    this.showDialog = function() {

        var instance = $uibModal.open({
            templateUrl: '/templates/main/auth/login-dialog.html',
            controller: 'LoginDialogCtrl',
            controllerAs: 'login'
        });

        return instance.result;

    };

}]);
