angular.module('tmaps.toolwindow')
/**
 * A directive widget to assign cell selections to classes.
 * Usage:
 *
 *  <tm-class-selection-widget
 *    selections="selections"
 *    on-change="classes = classes">
 *  </tm-class-selection-widget>
 *
 * Arguments:
 *  - selections: an array of CellSelection objects.
 *  - on-change: an expression whose RHS can contain a variable 'classes', that
 *    is updated whenever a selection changes or the widget's state was altered.
 *    This variable points to an array with the structure:
 *
 *    [
 *      // Class 1:
 *      {
 *        cells: [int, int, ...],
 *        color: string (as specified by the colormap)
 *      },
 *      ...
 *    ]
 *
 */
.directive('tmClassSelectionWidget', function() {
    return {
        restrict: 'E',
        scope: {
            selections: '=',
            onChangeExpr: '&onChange'
        },
        templateUrl: '/templates/tools/widgets/tm-class-selection-widget.html',
        controller: ['$http', '$scope', 'tmapsProxy',
            function($http, $scope, tmapsProxy) {

            // Add a default class label to each selection
            _($scope.selections).each(function(sel, i) {
                sel.viewProps = {
                    class: 'CLASS_' + i
                };
            });

            $scope.classArray = [];

            $scope.updateClasses = function() {
                var classes = {};
                $scope.selections.forEach(function(sel) {
                    var clsName = sel.viewProps.class;
                    if (clsName) {
                        if (_.isUndefined(classes[clsName])) {
                            classes[clsName] = {
                                cells: []
                            };
                        }
                        classes[clsName].cells = classes[clsName].cells.concat(
                            sel.getCells()
                        );
                        if (!classes[clsName].color) {
                            classes[clsName].color = sel.getColor().toRGBArray();
                        }
                    }
                });

                $scope.onChangeExpr({
                    classes: classes
                });

                var clsArray = [];
                _(classes).each(function(classObj, clsName) {
                    clsArray.push({
                        name: clsName,
                        cellIds: classObj.cells
                    });
                });
                $scope.classArray = clsArray;
            };

            // Update the 'classes' variable in the expression
            // for the first time. This will set the class assignments
            // to the default ones.
            $scope.updateClasses();

            // Update the classes whenever a selection changes.
            // This ensures that the onChange expression is up to date.
            tmapsProxy.$rootScope.$on('cellSelectionChanged', function(sel) {
                $scope.updateClasses();
            });
        }]
    };
});
