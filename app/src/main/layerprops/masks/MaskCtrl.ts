class MaskCtrl {
    static $inject = ['$scope', 'colorFactory'];

    opacityInput: number;
    colorInput: string;
    colors: Color[]

    constructor(private $scope, private colorFty) {

        // Initialize the input models
        this.opacityInput = this.$scope.layer.opacity() * 100;
        this.colorInput = $scope.layer.color().toHex();

        // Colors that can be chosen form the color picker.
        // Make sure that #ffffff (white) is available.
        var hexColors = [
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

        this.colors = _.map(hexColors, (hex) => {
            return this.colorFty.createFromHex(hex);
        });

        this.$scope.$watch('ctrl.colorInput', (newVal) => {
            var newColor = this.colorFty.createFromHex(newVal);
            $scope.layer.color(newColor);
        });

    }
}

angular.module('tmaps.main.layerprops.masks').controller('MaskCtrl', MaskCtrl);

