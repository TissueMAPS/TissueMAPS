interface ViewerScope extends ViewerWindowScope {
    viewer: Viewer;
    viewerCtrl: ViewerCtrl;
}

class ViewerCtrl {
    static $inject = ['$scope'];

    maxT: number;
    minT: number;
    tStep: number;
    maxZ: number;
    minZ: number;
    zStep: number;

    get currentTpoint() {
        return this.$scope.viewer.currentTpoint;
    }
    set currentTpoint(t) {
        this.$scope.viewer.currentTpoint = Math.floor((t - this.tStep) / this.tStep);
    }

    get currentZplane() {
        return this.$scope.viewer.currentZplane;
    }
    set currentZplane(z) {
        this.$scope.viewer.currentZplane = Math.floor((z - this.zStep) / this.zStep);
    }

    constructor(public $scope: ViewerScope) {
        $scope.viewer = $scope.viewer;
        this.zStep = 10;
        this.tStep = 10;
        // The slider won't be able to set currentZplane/currentTpoint to 0 if
        // the knob is all the way to the left. Therefore
        // we set 0 to be zStep/tStep and substract this value before
        // settings the current zplane/tpoint on the viewer.
        this.maxT = $scope.viewer.maxT * this.tStep + this.tStep;
        this.minT = this.tStep;
        this.maxZ = $scope.viewer.maxZ * this.zStep + this.zStep;
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
