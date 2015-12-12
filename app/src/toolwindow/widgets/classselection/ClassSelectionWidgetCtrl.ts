interface Class {
    name: string;
    selection: MapObjectSelection;
}

class ClassSelectionWidgetCtrl {
    static $inject = ['$scope', 'tmapsProxy'];

    selHandler: MapObjectSelectionHandler;
    toolOptions: ToolOptions;

    private _classes: {[objectType: string]: Class[];} = {};

    constructor($scope: ToolContentScope, tmapsProxy: TmapsProxy) {
        this.selHandler = tmapsProxy.appInstance.mapObjectSelectionHandler;
        this.toolOptions = $scope.toolOptions;
    }

    /**
     * To be called from the controller using this widget, e.g.:
     * var theClasses = $scope.classSelectionWidget.classes;
     */
    get classes() {
        var cls = this._classes[this.toolOptions.chosenMapObjectType];
        return cls === undefined ? [] : cls;
    }

    getClassesForChosenType(): Class[] {
        return this._classes[this.toolOptions.chosenMapObjectType];
    }

    getSelectionsForChosenType() {
        return this.selHandler.getSelectionsForType(this.toolOptions.chosenMapObjectType);
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

class ClassSelectionCtrl {
    static $inject = ['$scope'];

    useAsClass: boolean = false;
    className: string;

    constructor($scope) {
        // Above one level is the scope introduced for the current ng-repeat,
        // one lever further is the scope that is used by the classSelectionWidget ctrl.
        $scope.$watch('sel.className', (newVal) => {
            if (newVal !== undefined && newVal !== '') {
                this.useAsClass = true;
                $scope.classSelectionWidget.updateClassName($scope.objSelection, this.className);
            } else {
                this.useAsClass = false;
            }
        });
        $scope.$watch('sel.useAsClass', (doUse) => {
            if (doUse !== undefined && doUse) {
                $scope.classSelectionWidget.registerSelectionAsClass($scope.objSelection, this.className);
            } else {
                $scope.classSelectionWidget.deregisterSelection($scope.objSelection);
            }
        });

    }
}

angular.module('tmaps.toolwindow').controller('ClassSelectionWidgetCtrl', ClassSelectionWidgetCtrl);
angular.module('tmaps.toolwindow').controller('ClassSelectionCtrl', ClassSelectionCtrl);

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
