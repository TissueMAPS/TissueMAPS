// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
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
class ViewersTabbarCtrl {
    static $inject = ['$scope'];

    constructor(private $scope: ViewerWindowScope) {}

    clickTab(viewer: Viewer) {
        this.$scope.viewerWindowCtrl.selectViewer(viewer);
    }

    clickDelete(viewer: Viewer) {
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
