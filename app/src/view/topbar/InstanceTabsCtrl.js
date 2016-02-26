angular.module('tmaps.ui')
.controller('InstanceTabsCtrl', ['application', function(application) {

    this.appInstances = application.appInstances;

    this.clickTab = function(index) {
        application.setActiveAppInstanceByNumber(index);
        var name = application.getActiveAppInstance().experiment.name;
    };

    // TODO: Add dialog "Are you sure?"
    this.removeTab = function(index) {
        application.removeAppInstance(index);
    };

    this.isActiveAppInstance = function(index) {
        return application.getActiveAppInstanceNumber() == index;
    };
}]);
