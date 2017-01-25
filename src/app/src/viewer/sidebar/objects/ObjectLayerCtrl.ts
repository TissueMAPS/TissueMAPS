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
class ObjectLayerCtrl {

    mapobjectType: MapobjectType;
    inRenamingMode: boolean;

    private _opacityInput: number;
    private _origName: string;
    private _$stateParams: any;

    get opacityInput() {
        return this._opacityInput;
    }

    set opacityInput(v: number) {
        this._opacityInput = v;
        this.mapobjectType.layers.forEach((l) => {
            l.opacity = v / 100;
        })
    }

    selectableColors = [
        '#e41a1c',
        '#377eb8',
        '#4daf4a',
        '#984ea3',
        '#ff7f00',
        '#ffffff'
    ];

    selectedColor: { fillColor: string; strokeColor: string; } = {
        fillColor: undefined,
        strokeColor: undefined
    };

    static $inject = ['$scope'];


    changeName() {
        var dao = new MapobjectTypeDAO(this._$stateParams.experimentid);
        var newName = this.mapobjectType.name.replace(/[^-A-Z0-9]+/ig, "_");
        dao.update(this.mapobjectType.id, {
            name: newName
        }).then(() => {
            // Replace all special characters by underscore
            this.mapobjectType.name = newName;
        }, () => {
            this.mapobjectType.name = this._origName;
        });
    }

    toggleRenamingMode() {
        this.inRenamingMode = !this.inRenamingMode;
    }

    constructor($scope: any) {
        this._$stateParams = $injector.get<any>('$stateParams');
        this.inRenamingMode = false;
        this.mapobjectType = $scope.mapobjectType;
        this.opacityInput = this.mapobjectType.layers[0].opacity * 100;
        this._origName = this.mapobjectType.name;
        $scope.$watch('layerCtrl.selectedColor.fillColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                this.mapobjectType.layers.forEach((l) => {
                    l.fillColor = Color.fromHex(<string>newVal);
                });
            }
        });
        $scope.$watch('layerCtrl.selectedColor.strokeColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                this.mapobjectType.layers.forEach((l) => {
                    l.strokeColor = Color.fromHex(<string>newVal);
                });
            }
        });
        // Initialize the selected color of each property based on the color
        // that is already assigned to this property.
        this.selectedColor.fillColor = this.mapobjectType.layers[0].fillColor.toHex();
        this.selectedColor.strokeColor = this.mapobjectType.layers[0].strokeColor.toHex();
    }
}

angular.module('tmaps.ui').controller('ObjectLayerCtrl', ObjectLayerCtrl);
