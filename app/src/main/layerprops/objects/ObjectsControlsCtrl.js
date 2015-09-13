angular.module('tmaps.main.layerprops.objects')
.controller('ObjectsControlsCtrl',
            ['$scope', function($scope) {

    this.removeSelectedLayers = function() {
        _($scope.selectionBox.getSelectedItems()).each(function(layer) {
            $scope.objCtrl.appInstance.removeObjectLayer(layer);
        });
    };

}]);

