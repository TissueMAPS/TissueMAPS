angular.module('tmaps.ui')
/**
 * A controller to manage the control bar in the channel settings
 * section of the sidebar.
 * This controller has access to the selected items (= channel layers in
 * this case) since it is part of the selection box.
 */
.controller('ChannelControlsCtrl',
            ['$scope', 'removeLayerService',
            function($scope, removeLayerService) {

    this.removeSelectedChannels = function() {
        var sel = $scope.selectionBox.getSelectedItems();
        removeLayerService.removeChannelsAfterPrompt(sel);
    };

}]);

