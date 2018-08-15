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
interface ViewportScope extends ViewerScope {
    viewport: Viewport;
    viewportCtrl: ViewportCtrl;
}

class ViewportCtrl {
    static $inject = ['$scope'];
    constructor(private _$scope: ViewportScope) {
        this._$scope.viewport = this._$scope.viewer.viewport;
    }
}
angular.module('tmaps.ui').controller('ViewportCtrl', ViewportCtrl);

angular.module('tmaps.ui')
.directive('tmViewport', [function() {
    return {
        restrict: 'EA',
        controller: 'ViewportCtrl',
        controllerAs: 'viewportCtrl',
        bindToController: true,
        templateUrl: '/src/viewer/viewport.html',
        link: function(scope, elem, attr) {
            /**
             * Call the viewport instance of this viewer to create the openlayers map.
             * This will cause the map to be injected into the DOM in the map container
             * DIV. After this the map promise on the viewport will be resolved.
             */
            var htmlElem = elem.find('.map-container').get(0);
            scope.viewer.viewport.renderMap(htmlElem);
        }
    };
}]);
