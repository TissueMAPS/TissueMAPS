// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
interface ViewerScope extends ViewerWindowScope {
    viewer: Viewer;
    viewerCtrl: ViewerCtrl;
}

class ViewerCtrl {
    static $inject = ['$scope'];

    minT: number;
    minZ: number;
    tStep: number;
    zStep: number;

    constructor(public $scope: ViewerScope) {
        $scope.viewer = $scope.viewer;  // ???
        this.zStep = 10;
        this.tStep = 10;
        // The slider won't be able to set currentZplane/currentTpoint to 0 if
        // the knob is all the way to the left. Therefore
        // we set 0 to be zStep/tStep and substract this value before
        // settings the current zplane/tpoint on the viewer.
        this.minT = this.tStep;
        this.minZ = this.zStep;
        // We need to evaluate maxT and maxZ outside of the constructor, because
        // by the time it gets called, the channel information may not have
        // available to the viewer and would result in wrong values.
    }

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

    get maxT(): number {
        return this.$scope.viewer.maxT * this.tStep + this.tStep;
    }

    get maxZ(): number {
        return this.$scope.viewer.maxZ * this.zStep + this.zStep;
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
