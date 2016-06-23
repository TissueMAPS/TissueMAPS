class ObjectLayerCtrl {

    layer: SegmentationLayer;

    private _opacityInput: number;

    get opacityInput() {
        return this._opacityInput;
    }

    set opacityInput(v: number) {
        this._opacityInput = v;
        this.layer.opacity = v / 100;
    }

    selectableColors = [ 
        '#e41a1c',
        '#377eb8',
        '#4daf4a',
        '#984ea3',
        '#ff7f00',
        '#ffffff'
    ];

    selectedColor: { fillColor: string; strokeColor: string; } = {
        fillColor: undefined,
        strokeColor: undefined
    };

    static $inject = ['$scope'];

    constructor($scope: any) {
        this.layer = $scope.layer;
        this.opacityInput = this.layer.opacity * 100;
        $scope.$watch('layerCtrl.selectedColor.fillColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                var fillColor = Color.fromHex(<string>newVal);
                this.layer.fillColor = fillColor;
            }
        });
        $scope.$watch('layerCtrl.selectedColor.strokeColor', (newVal, oldVal) => {
            if (newVal !== oldVal && newVal !== undefined) {
                var strokeColor = Color.fromHex(<string>newVal);
                this.layer.strokeColor = strokeColor;
            }
        });
        // Initialize the selected color of each property based on the color
        // that is already assigned to this property.
        this.selectedColor.fillColor = this.layer.fillColor.toHex();
        this.selectedColor.strokeColor = this.layer.strokeColor.toHex();
    }
}

angular.module('tmaps.ui').controller('ObjectLayerCtrl', ObjectLayerCtrl);
