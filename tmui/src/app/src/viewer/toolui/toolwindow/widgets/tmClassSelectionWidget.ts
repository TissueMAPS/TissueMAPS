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
angular.module('tmaps.ui')
.directive('tmClassSelectionWidget', function() {
    return {
        restrict: 'E',
        templateUrl: '/src/viewer/toolui/toolwindow/widgets/tm-class-selection-widget.html',
        controller: 'ClassSelectionWidgetCtrl',
        controllerAs: 'classSelectionWidget',
        bindToController: true,
        scope: true
    };
});

interface Class {
    name: string;
    mapobjectIds: number[];
    color: Color;
}

class ClassSelectionWidgetCtrl {
    static $inject = ['$scope'];

    private _controllers: {[objectType: string]: ClassSelectionCtrl[];} = {};

    constructor(public $scope: ToolWindowContentScope) {
        this.$scope.$parent['classSelectionWidget'] = this;
    }

    private get _viewer() {
        var parentScope = <ToolWindowContentScope> this.$scope.$parent;
        return parentScope.viewer;
    }

    private get _selectedMapobjectType() {
        var parentScope = this.$scope.$parent;
        var objectTypeWidget: MapobjectTypeWidgetCtrl =
            parentScope['mapobjectTypeWidget'];
        return objectTypeWidget.selectedType;
    }

    private _classes: Class[] = [];

    /**
     * Step through all selection controllers and check if the selections
     * should be used during training.
     * If yes, then the mapobjects contained in the selection should
     * be added to the class object.
     */
    private _computeClasses() {
        var clsMap = {};
        for (var objType in this._controllers) {
            var ctrls = this._controllers[objType];
            ctrls.forEach((ctrl) => {
                if (ctrl.useAsClass) {
                    if (clsMap[ctrl.className] === undefined) {
                        clsMap[ctrl.className] = {
                            mapobjectIds: [],
                            color: ctrl.selection.color
                        };
                    }
                    var mapobjectIds = ctrl.selection.mapObjects.map((o) => {
                        return o.id;
                    });
                    Array.prototype.push.apply(clsMap[ctrl.className].mapobjectIds, mapobjectIds); 
                }
            });
        }

        var classes: Class[] = [];
        for (var clsName in clsMap) {
            classes.push({
                name: clsName,
                mapobjectIds: clsMap[clsName].mapobjectIds,
                color: clsMap[clsName].color
            });
        }

        return classes;
    }

    get classes(): Class[] {
        var classes = this._computeClasses();
        if (this._classes.length != classes.length) {
            this._classes = classes;
        }
        return this._classes;
    }

    get selections() {
        var selectedType = this._selectedMapobjectType;
        var selHandler = this._viewer.mapObjectSelectionHandler;
        return selHandler.getSelectionsForType(selectedType);
    }

    deregisterSelectionCtrl(selCtrl: ClassSelectionCtrl) {
        var objType = selCtrl.selection.mapObjectType;
        if (this._controllers[objType] !== undefined) {
            var idx = this._controllers[objType].indexOf(selCtrl);
            if (idx > -1) {
                this._controllers[objType].splice(idx, 1);
            }
        }
    }

    registerSelectionCtrl(selCtrl: ClassSelectionCtrl) {
        var objType = selCtrl.selection.mapObjectType;
        if (this._controllers[objType] === undefined) {
            this._controllers[objType] = [];
        }
        this._controllers[objType].push(selCtrl);
    }

    recomputeClasses() {
        this._classes = this._computeClasses();
    }
}
angular.module('tmaps.ui').controller('ClassSelectionWidgetCtrl', ClassSelectionWidgetCtrl);

class ClassSelectionCtrl {
    static $inject = ['$scope'];

    useAsClass: boolean = true;
    className: string;
    get selection() {
        return this._$scope.objSelection;
    }

    constructor(private _$scope) {
        this.className = 'Class_' + _$scope.$index;
        _$scope.classSelectionWidget.registerSelectionCtrl(this);
        _$scope.$on('$destroy', () => {
            _$scope.classSelectionWidget.deregisterSelectionCtrl(this);
        });
        _$scope.$watch('sel.className', (newName, oldName) => {
            if (newName !== oldName) {
                this._$scope.classSelectionWidget.recomputeClasses();
            }
        })
        _$scope.$watch('sel.selection.mapObjects.length', () => {
            console.log('NEW VAL');
            this._$scope.classSelectionWidget.recomputeClasses();
        });
    }
}
angular.module('tmaps.ui').controller('ClassSelectionCtrl', ClassSelectionCtrl);
