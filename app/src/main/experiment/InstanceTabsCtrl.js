angular.module('tmaps.main.experiment')
.controller('InstanceTabsCtrl', ['application', function(application) {

    this.clickTab = function(index) {
        application.setActiveInstanceByNumber(index);
        var name = application.getActiveInstance().experiment.name;
    };

    // TODO: Add dialog "Are you sure?"
    this.removeTab = function(index) {
        application.removeInstance(index);
    };
}]);
