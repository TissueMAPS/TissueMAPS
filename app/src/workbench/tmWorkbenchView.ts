// the ViewCtrl on the tm-view div enables control over everything view related.
// For example, broadcasting messages to all UI elements in the view can be made using 
// $scope.viewCtrl.broadcast(msg, data);
angular.module('tmaps.ui').directive('tmWorkbenchWindowView', [function() {
    return {
        restrict: 'EA',
        controller: 'WorkbenchViewCtrl',
        controllerAs: 'workbenchViewCtrl',
        bindToController: true
    };
}]);

interface WorkbenchViewScope extends ng.IScope {

}

class WorkbenchViewCtrl {
    static $inject = ['$scope'];

    constructor(public $scope: WorkbenchViewScope) {

    }

    broadcast(message: string, data: any) {
        this.$scope.$broadcast(message, data);
    }

}
angular.module('tmaps.ui').controller('WorkbenchViewCtrl', WorkbenchViewCtrl);
