class VisualLayerCtrl {

    selectableColors: string[];

    supportedColorProperties = [
        {
            label: 'Fill color',
            property: 'fillColor'
        },
        {
            label: 'Stroke color',
            property: 'strokeColor'
        }
    ];

    selectedColor: { fillColor: string; strokeColor: string; } = {
        fillColor: undefined,
        strokeColor: undefined
    };

    static $inject = ['$scope'];

    constructor($scope: any) {
        var layer: VisualLayer = $scope.layer;

        // Colors that can be selected from the settings popup
        // to use as fillColor/strokeColor/etc.
        this.selectableColors = [
            '#ffffff',
            '#468966',
            '#FFF0A5',
            '#FFB03B',
            '#B64926',
            '#8E2800',
            '#e1e1e1'
        ];

        // TODO: Temporary solution. A VisualLayer could include other visuals than ColorizableVisual that have a fill-/strokeColor.
        // Also, the style arguments should maybe be settable on the layer
        // itself, and Visuals will just inherit them (as is the case
        // with the unwrapped openlayers classes).
        $scope.$watch('layerCtrl.selectedColor.fillColor', function(newVal, oldVal) {
            if (newVal !== oldVal && newVal !== undefined) {
                // When white is selected it defaults back to "no" filling, 
                // i.e. high transparency
                if (newVal == '#ffffff') {
                    var fillColor = Color.WHITE.withAlpha(0.02);
                } else {
                    var fillColor = Color.fromHex(<string>newVal);
                }
                console.log('changed fill color: ', fillColor)
                layer.visuals.forEach((v: ColorizableVisual) => {
                    v.fillColor = fillColor;
                });
            }
        });
        $scope.$watch('layerCtrl.selectedColor.strokeColor', function(newVal, oldVal) {
            if (newVal !== oldVal && newVal !== undefined) {
                var strokeColor = Color.fromHex(<string>newVal);
                layer.visuals.forEach((v: ColorizableVisual) => {
                    v.strokeColor = strokeColor;
                });
            }
        });

        // Initialize the selected color of each property based on the color
        // that is already assigned to this property.
        var sampleVisual = <ColorizableVisual> layer.visuals[0];
        this.selectedColor.fillColor = sampleVisual.fillColor.toHex();
        this.selectedColor.strokeColor = sampleVisual.strokeColor.toHex();
        // this.supportedColorProperties.forEach((color) => {
        //     var layerSupportsProperty = layer[color.property] !== undefined;
        //     if (layerSupportsProperty) {
        //         // TODO: If the original color of this property isn't in the selectableColors array,
        //         // then this will lead to an invalid selected color.
        //         this.selectedColor[color.property] = layer[color.property].toHex();

        //         $scope.$watch('layerCtrl.selectedColor[' + color.property + ']', function(newVal, oldVal) {
        //             // TODO: Two-way binding won't work: if this property changes somewhere else, this won't be
        //             // represented in the selcted color of the color picker widget.
        //             if (newVal !== oldVal) {
        //                 layer[color.property] = Color.fromHex(newVal);
        //             }
        //         });
        //     }
        // });
    }
}

angular.module('tmaps.ui').controller('VisualLayerCtrl', VisualLayerCtrl);
