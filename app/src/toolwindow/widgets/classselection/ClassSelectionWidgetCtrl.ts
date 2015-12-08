interface Class {
    name: string;
    selection: MapObjectSelection;
}

class ClassSelectionWidgetCtrl {
    static $inject = ['$scope', 'tmapsProxy'];

    private _classes: {[objectType: string]: Class[];} = {};

    selHandler: MapObjectSelectionHandler;
    chosenMapObjectType: MapObjectType = '';

    /**
     * To be called from the controller using this widget, e.g.:
     * var theClasses = $scope.selWidget.classes;
     */
    get classes() {
        var cls = this._classes[this.chosenMapObjectType];
        return cls === undefined ? [] : cls;
    }

    getClassesForChosenType(): Class[] {
        return this._classes[this.chosenMapObjectType];
    }

    getSelectionsForChosenType() {
        return this.selHandler.getSelectionsForType(this.chosenMapObjectType);
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

    constructor($scope, tmapsProxy) {
        this.selHandler = tmapsProxy.appInstance.mapObjectSelectionHandler;
        window['scope'] = $scope;
    }
}

class ClassSelectionCtrl {
    static $inject = ['$scope'];

    useAsClass: boolean = false;
    className: string;

    constructor($scope) {
        // Above one level is the scope introduced for the current ng-repeat,
        // one lever further is the scope that is used by the selWidget ctrl.
        $scope.$watch('sel.className', (newVal) => {
            if (newVal !== undefined && newVal !== '') {
                this.useAsClass = true;
                $scope.selWidget.updateClassName($scope.objSelection, this.className);
            } else {
                this.useAsClass = false;
            }
        });
        $scope.$watch('sel.useAsClass', (doUse) => {
            if (doUse !== undefined && doUse) {
                $scope.selWidget.registerSelectionAsClass($scope.objSelection, this.className);
            } else {
                $scope.selWidget.deregisterSelection($scope.objSelection);
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
