// the ViewCtrl on the tm-view div enables control over everything view related.
// For example, broadcasting messages to all UI elements in the view can be made using 
// $scope.viewCtrl.broadcast(msg, data);
angular.module('tmaps.ui').directive('tmViewerWindowView', [function() {
    return {
        restrict: 'EA',
        controller: 'ViewerWindowCtrl',
        controllerAs: 'viewerWindowCrtl',
        bindToController: true
    };
}]);

interface ViewerWindowScope extends ng.IScope {

}

class ViewerWindowCtrl {
    static $inject = ['$scope'];

    constructor(public $scope: ViewerWindowScope) {

    }

    broadcast(message: string, data: any) {
        this.$scope.$broadcast(message, data);
    }

}
angular.module('tmaps.ui').controller('ViewerWindowCtrl', ViewerWindowCtrl);
