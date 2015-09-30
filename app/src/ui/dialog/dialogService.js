angular.module('tmaps.ui')
.service('dialogService', ['$modal', '$q', function($modal, $q) {

    function showDialog(title, message) {
        var instance = $modal.open({
            templateUrl: '/templates/main/dialog/dialog.html',
            controller: 'DialogCtrl',
            controllerAs: 'dialog',
            resolve: {
                title: function() { return title; },
                message: function() { return message; }
            }
        });

        return instance.result;
    }

    this.error = function(message) {
        return showDialog('Error', message);
    };

    this.warning = function(message) {
        return showDialog('Warning', message);
    };

}]);
