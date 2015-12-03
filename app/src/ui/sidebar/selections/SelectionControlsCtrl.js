// angular.module('tmaps.ui')
// /**
//  * A controller to manage the control bar in the selections settings
//  * section of the sidebar.
//  * This controller has access to the selected items (= selections in
//  * this case) since it is part of the selection box.
//  */
// .controller('SelectionControlsCtrl',
//             ['$scope', function($scope) {

//     var selHandler = $scope.selCtrl.viewport.selectionHandler;

//     this.clearSelectedSelections = function() {
//         _($scope.selectionBox.getSelectedItems()).each(function(s) {
//             s.clear();
//         });
//     };

//     this.deleteSelectedSelections = function() {
//         console.log('aasdf');
//         // Deselect the layer before removing it, otherwise
//         // the activeSelectionId may point to a nonexistant selection
//         _($scope.selectionBox.getSelectedItems()).each(function(s) {
//             if (selHandler.activeSelectionId === s.id) {
//                 selHandler.activeSelectionId = -1;
//             }
//             selHandler.removeSelectionById(s.id);
//         });
//     };


// }]);

