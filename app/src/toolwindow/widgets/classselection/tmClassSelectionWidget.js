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
        templateUrl: '/templates/tools/widgets/tm-class-selection-widget.html',
        controller: 'ClassSelectionWidgetCtrl',
        controllerAs: 'selWidget'
    };
});
