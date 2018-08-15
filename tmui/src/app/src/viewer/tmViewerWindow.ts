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
// the ViewCtrl on the tm-view div enables control over everything view related.
// For example, broadcasting messages to all UI elements in the view can be made using 
// $scope.viewCtrl.broadcast(msg, data);
angular.module('tmaps.ui').directive('tmViewerWindow', [function() {
    return {
        restrict: 'EA',
        controller: 'ViewerWindowCtrl',
        scope: true,
        controllerAs: 'viewerWindowCtrl',
        bindToController: true
    };
}]);

interface ViewerWindowScope extends ng.IScope {
    viewerWindowCtrl: ViewerWindowCtrl;
}

class ViewerWindowCtrl {
    static $inject = ['$scope', 'application', '$document'];

    private viewers: Viewer[];

    constructor(public $scope: ViewerWindowScope,
                private application: Application,
                private $document: ng.IDocumentService) {
        this.viewers = application.viewers;
    }

    selectViewer(viewer: Viewer) {
        this.application.showViewer(viewer);
    }

    deleteViewer(viewer: Viewer) {
        this.application.removeViewer(viewer);
    }

}
angular.module('tmaps.ui').controller('ViewerWindowCtrl', ViewerWindowCtrl);
