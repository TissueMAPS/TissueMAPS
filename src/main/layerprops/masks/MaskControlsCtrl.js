angular.module('tmaps.main.layerprops.masks')
/**
 * A controller to manage the control bar in the mask settings
 * section of the sidebar.
 * This controller has access to the selected items (= mask layers in
 * this case) since it is part of the selection box.
 */
.controller('MaskControlsCtrl',
            ['$scope', 'removeLayerService',
            function($scope, removeLayerService) {

    this.removeSelectedLayers = function() {
        var sel = $scope.selectionBox.getSelectedItems();
        removeLayerService.removeMasksAfterPrompt(sel);
    };

}]);


