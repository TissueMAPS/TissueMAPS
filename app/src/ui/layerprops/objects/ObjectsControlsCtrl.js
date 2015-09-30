angular.module('tmaps.ui')
.controller('ObjectsControlsCtrl',
            ['$scope', function($scope) {

    this.removeSelectedLayers = function() {
        _($scope.selectionBox.getSelectedItems()).each(function(layer) {
            $scope.objCtrl.viewport.removeObjectLayer(layer);
        });
    };

}]);

