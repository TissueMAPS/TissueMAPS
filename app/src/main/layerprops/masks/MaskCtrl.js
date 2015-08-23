angular.module('tmaps.main.layerprops.masks')
.controller('MaskCtrl', ['$scope', 'colorUtil', function($scope, colorUtil) {

    // Initialize the input models
    this.opacityInput = $scope.layer.opacity() * 100;
    this.colorInput = colorUtil.rgbToHex($scope.layer.color());

    // Colors that can be chosen form the color picker.
    // Make sure that #ffffff (white) is available.
    this.colors = [
        '#7bd148',
        '#5484ed',
        '#a4bdfc',
        '#46d6db',
        '#7ae7bf',
        '#51b749',
        '#fbd75b',
        '#ffb878',
        '#ff887c',
        '#dc2127',
        '#dbadff',
        '#ffffff'
    ];

    function setColorFromHex(layer, hexColor) {
        var rgb = colorUtil.hexToRgb(hexColor);
        if (rgb) {
            layer.color(rgb);
        } else {
            console.log('Warning: no valid color ', rgb);
        }
    }

    $scope.$watch('ctrl.colorInput', function(newVal) {
        setColorFromHex($scope.layer, newVal);
    });

}]);
