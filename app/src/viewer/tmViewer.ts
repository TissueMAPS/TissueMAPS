interface ViewerScope extends ViewerWindowScope {
    // FIXME: Remove this.
    appInstance: AppInstance;
    viewer: AppInstance;
}

class ViewerCtrl {
    static $inject = ['$scope'];
    constructor(public $scope: ViewerScope) {
        $scope.appInstance = $scope.viewer;
        // FIXME. Should be set via tabs
    }
}

angular.module('tmaps.ui').directive('tmViewer', [function() {
    return {
        restrict: 'EA',
        controller: ViewerCtrl,
        controllerAs: 'viewerCtrl',
        bindToController: true,
        templateUrl: '/src/viewer/tm-viewer.html'
    };
}]);
