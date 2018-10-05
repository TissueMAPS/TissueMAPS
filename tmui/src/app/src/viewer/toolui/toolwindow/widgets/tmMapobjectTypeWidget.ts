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
angular.module('tmaps.ui')
.directive('tmMapobjectTypeWidget', () => {
    var template = 
        '<label>Object type: </label>' +
        '<select ng-model="mapobjectTypeWidget.selectedType" ng-options="t for t in mapobjectTypeWidget.mapobjectTypeNames">' +
        '</select>';
    return {
        restrict: 'E',
        template: template,
        controller: 'MapobjectTypeWidgetCtrl',
        controllerAs: 'mapobjectTypeWidget',
        scope: true
    };
});

class MapobjectTypeWidgetCtrl {

    static $inject = ['$scope'];

    mapobjectTypeNames: string[] = [];

    constructor(private _$scope: any) {
        this._$scope.$parent['mapobjectTypeWidget'] = this;
        this.mapobjectTypeNames = this._$scope.viewer.mapobjectTypes.map((t) => {
            return t.name;
        });
    }

    get selectedType() {
        return this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType;
    }

    set selectedType(t: string) {
        this._$scope.viewer.mapObjectSelectionHandler.activeMapObjectType = t;
    }
}

angular.module('tmaps.ui').
controller('MapobjectTypeWidgetCtrl', MapobjectTypeWidgetCtrl);
