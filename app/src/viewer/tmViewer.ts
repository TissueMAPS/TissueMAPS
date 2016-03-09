interface ViewerScope extends ViewerWindowScope {
    // FIXME: Remove this.
    appInstance: AppInstance;
    viewer: AppInstance;
    viewerCtrl: ViewerCtrl;
}

class ViewerCtrl {
    static $inject = ['$scope'];
    constructor(public $scope: ViewerScope) {
        $scope.appInstance = $scope.viewer;
    }
}

angular.module('tmaps.ui').directive('tmViewer', [function() {
    return {
        restrict: 'EA',
        scope: true,
        controller: ViewerCtrl,
        controllerAs: 'viewerCtrl',
        bindToController: true,
        templateUrl: '/src/viewer/tm-viewer.html'
    };
}]);
