class ViewersTabbarCtrl {
    static $inject = ['$scope'];

    constructor(private $scope: ViewerWindowScope) {}

    clickTab(viewer: AppInstance) {
        this.$scope.viewerWindowCtrl.selectViewer(viewer);
    }

    clickDelete(viewer: AppInstance) {
        this.$scope.viewerWindowCtrl.deleteViewer(viewer);
    }
}

angular.module('tmaps.ui').controller('ViewersTabbarCtrl', ViewersTabbarCtrl);

angular.module('tmaps.ui')
.directive('tmViewersTabbar', [function() {
    return {
        restrict: 'EA',
        controller: 'ViewersTabbarCtrl',
        controllerAs: 'viewersTabbarCtrl',
        templateUrl: '/src/viewer/tm-viewers-tabbar.html',
        bindToController: true
    };
}]);
