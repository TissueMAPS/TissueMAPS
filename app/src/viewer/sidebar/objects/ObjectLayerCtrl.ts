class ObjectLayerCtrl {

    selectableColors = [
        '#ffffff',
        '#468966',
        '#FFF0A5',
        '#FFB03B',
        '#B64926',
        '#8E2800',
        '#e1e1e1'
    ];

    selectedColor: { fillColor: string; strokeColor: string; } = {
        fillColor: undefined,
        strokeColor: undefined
    };

    static $inject = ['$scope'];

    constructor($scope: any) {
        $scope.$watch('layerCtrl.selectedColor.fillColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                var fillColor = Color.fromHex(<string>newVal);
                $scope.layer.fillColor = fillColor;
            }
        });
        $scope.$watch('layerCtrl.selectedColor.strokeColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                var strokeColor = Color.fromHex(<string>newVal);
                $scope.layer.strokeColor = strokeColor;
            }
        });
        // Initialize the selected color of each property based on the color
        // that is already assigned to this property.
        this.selectedColor.fillColor = $scope.layer.fillColor.toHex();
        this.selectedColor.strokeColor = $scope.layer.strokeColor.toHex();
    }
}

angular.module('tmaps.ui').controller('ObjectLayerCtrl', ObjectLayerCtrl);
