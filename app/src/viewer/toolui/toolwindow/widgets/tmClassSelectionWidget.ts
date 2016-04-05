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
    selection: MapObjectSelection;
}

class ClassSelectionWidgetCtrl {
    static $inject = ['$scope'];

    private _classes: {[objectType: string]: Class[];} = {};

    constructor(public $scope: ToolWindowContentScope) {
        this.$scope.$parent['classSelectionWidget'] = this;
    }

    private _getViewer() {
        var parentScope = <SVMScope> this.$scope.$parent;
        return parentScope.viewer;
    }

    private _getSelectedMapobjectType() {
        var parentScope = <SVMScope> this.$scope.$parent;
        return parentScope.objectNameWidget.selectedName;
    }

    /**
     * To be called from the controller using this widget, e.g.:
     * var theClasses = $scope.classSelectionWidget.classes;
     */
    get classes() {
        var selectedType = this._getSelectedMapobjectType();
        var cls = this._classes[selectedType];
        return cls === undefined ? [] : cls;
    }

    get selections() {
        var selectedType = this._getSelectedMapobjectType();
        var selHandler = this._getViewer().mapObjectSelectionHandler;
        return selHandler.getSelectionsForType(selectedType);
    }

    registerSelectionAsClass(sel: MapObjectSelection, className: string) {
        if (this._classes[sel.mapObjectType] === undefined) {
            this._classes[sel.mapObjectType] = [];
        }
        var classes = this._classes[sel.mapObjectType];
        classes.push({
            name: className,
            selection: sel
        });
    }

    updateClassName(sel: MapObjectSelection, className: string) {
        if (this._classes[sel.mapObjectType] !== undefined) {
            var classes = this._classes[sel.mapObjectType];
            var cl = _(classes).find((cl) => {
                return cl.selection == sel;
            });
            if (cl !== undefined) {
                cl.name = className;
            } else {
                console.log('Cannot update name of class, no such class.');
            }
        } else {
            console.log('Cannot update name of class, no such array of classes.');
        }
    }

    deregisterSelection(sel: MapObjectSelection) {
        var classes = this._classes[sel.mapObjectType];
        if (classes !== undefined) {
            var cl = _(classes).find((cl) => {
                return cl.selection == sel;
            });
            if (cl !== undefined) {
                var idx = classes.indexOf(cl);
                classes.splice(idx, 1);
            }
        }
    }

}
angular.module('tmaps.ui').controller('ClassSelectionWidgetCtrl', ClassSelectionWidgetCtrl);

class ClassSelectionCtrl {
    static $inject = ['$scope'];

    useAsClass: boolean = true;
    className: string;

    constructor($scope) {
        this.className = 'Class_' + $scope.$index;

        $scope.$watch('sel.className', (newVal) => {
            if (newVal !== undefined && newVal !== '') {
                this.useAsClass = true;
                $scope.classSelectionWidget.updateClassName(
                    $scope.objSelection,
                    this.className
                );
            } else {
                this.useAsClass = false;
            }
        });
        $scope.$watch('sel.useAsClass', (doUse) => {
            if (doUse !== undefined && doUse) {
                $scope.classSelectionWidget.registerSelectionAsClass(
                    $scope.objSelection, this.className
                );
            } else {
                $scope.classSelectionWidget.deregisterSelection(
                    $scope.objSelection
                );
            }
        });

    }
}
angular.module('tmaps.ui').controller('ClassSelectionCtrl', ClassSelectionCtrl);

//             // Add a default class label to each selection
//             _($scope.selections).each(function(sel, i) {
//                 sel.viewProps = {
//                     class: 'CLASS_' + i
//                 };
//             });

//             $scope.classArray = [];

//             $scope.updateClasses = function() {
//                 var classes = {};
//                 $scope.selections.forEach(function(sel) {
//                     var clsName = sel.viewProps.class;
//                     if (clsName) {
//                         if (_.isUndefined(classes[clsName])) {
//                             classes[clsName] = {
//                                 mapObjectIds: []
//                             };
//                         }
//                         classes[clsName].mapObjects = classes[clsName].mapObjectIds.concat(
//                             sel.getMapObjects().map(function(o) {
//                                 return o.id;
//                             })
//                         );
//                         if (!classes[clsName].color) {
//                             classes[clsName].color = sel.color.toOlColor();
//                         }
//                     }
//                 });

//                 $scope.onChangeExpr({
//                     classes: classes
//                 });

//                 var clsArray = [];
//                 _(classes).each(function(classObj, clsName) {
//                     clsArray.push({
//                         name: clsName,
//                         mapObjectIds: classObj.mapObjects
//                     });
//                 });
//                 $scope.classArray = clsArray;
//             };

//             // Update the 'classes' variable in the expression
//             // for the first time. This will set the class assignments
//             // to the default ones.
//             $scope.updateClasses();

//             // Update the classes whenever a selection changes.
//             // This ensures that the onChange expression is up to date.
//             tmapsProxy.viewportScope.then(function(scope) {
//                 scope.$on('cellSelectionChanged', function(sel) {
//                     $scope.updateClasses();
//                 });
//             });
//         }]
