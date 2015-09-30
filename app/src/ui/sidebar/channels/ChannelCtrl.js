angular.module('tmaps.ui')
.controller('ChannelCtrl', ['$scope', 'colorFactory', function($scope, colorFactory) {
    var self = this;

    // Call the exposed method of the boxCtrl
    function getSelectedLayers() {
        return $scope.selectionBox.getSelectedItems();
    }

    this.color = {
        RED:   colorFactory.create(255, 0, 0),
        GREEN: colorFactory.create(0, 255, 0),
        BLUE:  colorFactory.create(0, 0, 255)
    };

    this.setColor = function(layer, color) {
        if (layer.color().equals(color)) {
            // Same color was selected, unselect it by setting null.
            layer.color(null);
        } else {
            layer.color(color);
        }
    };

    this.isRed = function(layer) {
        return layer.color().equals(this.color.RED);
    };
    this.isGreen = function(layer) {
        return layer.color().equals(this.color.GREEN);
    };
    this.isBlue = function(layer) {
        return layer.color().equals(this.color.BLUE);
    };

    // Since two-way data binding isn't possible on the layer properties
    // with a ui-slider, the values are watched manually and the input model is
    // changed so that the slider accurately reflects the model state.
    // Note that the values stored on the layer object doesn't correspond to the
    // slider intervals, therefore they have to be readjusted (e.g. by
    // multiplying times 100 so that 0.5 * 100 = 50).

    // Initialize the input models
    this.maxInput = $scope.layer.max() * 255;
    this.minInput = $scope.layer.min() * 255;
    this.brightnessInput = $scope.layer.brightness() * 100;
    this.opacityInput = $scope.layer.opacity() * 100;

    // Setup watches
    // TODO: the slider for MAXIMUM doesn't work correctly. Isn't it set up properly?
    $scope.$watch('layer.max()', function(newVal) {
        self.maxInput = newVal * 255;
    });

    $scope.$watch('layer.min()', function(newVal) {
        self.minInput = newVal * 255;
    });

    $scope.$watch('layer.brightness()', function(newVal) {
        self.brightnessInput = newVal * 100;
    });

    $scope.$watch('layer.opacity()', function(newVal) {
        self.opacity = newVal * 100;
    });

    this.setDefaultSettings = function(layer) {
        this.setLayerMin(layer, 0);
        this.setLayerMax(layer, 1);
        this.setLayerBrightness(layer, 0);
        this.setLayerOpacity(layer, 1);
    };

    /**
     * The following methods set the layer property min to `val` for layer
     * and all other selected layers if there are such.
     */
    this.setLayerMin = function(layer, val) {
        if (_(getSelectedLayers()).contains(layer)) {
            getSelectedLayers().forEach(function(l) {
                l.min(val);
            });
        } else {
            layer.min(val);
        }
    };

    this.setLayerMax = function(layer, val) {
        if (_(getSelectedLayers()).contains(layer)) {
            getSelectedLayers().forEach(function(l) {
                l.max(val);
            });
        } else {
            layer.max(val);
        }
    };

    this.setLayerBrightness = function(layer, val) {
        if (_(getSelectedLayers()).contains(layer)) {
            getSelectedLayers().forEach(function(l) {
                l.brightness(val);
            });
        } else {
            layer.brightness(val);
        }
    };

    this.setLayerOpacity = function(layer, val) {
        if (_(getSelectedLayers()).contains(layer)) {
            getSelectedLayers().forEach(function(l) {
                l.opacity(val);
            });
        } else {
            layer.opacity(val);
        }
    };
}]);
