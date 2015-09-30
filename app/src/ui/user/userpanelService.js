angular.module('tmaps.ui')
.service('userpanelService', ['$modal', function($modal) {

    var instance = null;

    this.showPanel = function() {
        instance = $modal.open({
            templateUrl: '/templates/main/experiment/userpanel.html',
            controller: 'UserpanelCtrl',
            controllerAs: 'userpanel',
            windowClass: 'userpanel',
            keyboard: false,
            // windowTemplateUrl: '/templates/main/content-dialog.html'
            size: 'lg'
        });
    };

    this.hidePanel = function() {
        if (!_.isNull(instance)) {
            instance.dismiss(false);
            instance = null;
        }
    };

}]);
