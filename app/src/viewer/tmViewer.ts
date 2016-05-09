interface ViewerScope extends ViewerWindowScope {
    // FIXME: Remove this.
    viewer: Viewer;
    viewerCtrl: ViewerCtrl;
}

class ViewerCtrl {
    static $inject = ['$scope'];

    maxZ: number;
    minZ: number;
    zStep: number;

    get currentZplane() {
        return this.$scope.viewer.currentZplane;
    }
    set currentZplane(z) {
        this.$scope.viewer.currentZplane = Math.floor((z - this.zStep) / this.zStep);
    }

    constructor(public $scope: ViewerScope) {
        $scope.viewer = $scope.viewer;
        this.zStep = 10;
        // The slider won't be able to set currentZplane to 0 if
        // the knob is all the way to the left. Therefore
        // we set 0 to be zStep and substract this value before
        // settings the current zplane on the viewer.
        this.maxZ = $scope.viewer.experiment.maxZ * this.zStep + this.zStep;
        this.minZ = this.zStep;
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
