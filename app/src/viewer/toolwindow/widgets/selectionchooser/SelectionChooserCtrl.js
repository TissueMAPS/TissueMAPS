angular.module('tmaps.toolwindow')
.controller('SelectionChooserCtrl', ['$scope', function($scope) {

    var selHandler = $scope.viewport.selectionHandler;

    // TODO: Maybe this directive should use an isolate scope and only expose the var currentSelection
    $scope.selectedCells = undefined;
    var currentSelection = undefined;

    $scope.selections = function() {
        return selHandler.selections;
    };

    $scope.select = function(sel) {
        if (currentSelection == sel) {
            $scope.selectedCells = undefined;
            sel.viewProps.selected = false;
        } else {
            currentSelection = sel;
            $scope.selectedCells = sel.getCells();
            sel.viewProps.selected = true;
            selHandler.selections.forEach(function(s) {
                if (s !== sel) {
                    s.viewProps.selected = false;
                }
            });
        }
    };
}]);
