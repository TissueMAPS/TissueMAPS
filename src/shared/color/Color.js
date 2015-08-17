angular.module('tmaps.shared.color')
.factory('Color', ['colorUtil', function(colorUtil) {

    function Color(r, g, b, a) {
        this.r = parseInt(r);
        this.g = parseInt(g);
        this.b = parseInt(b);

        if (_.isUndefined(a)) {
            a = 1.0;
        }
        this.a = parseFloat(a);
    }

    Color.prototype.toRGBArray = function() {
        return [this.r, this.g, this.b];
    };

    Color.prototype.toRGBAArray = function() {
        return [this.r, this.g, this.b, this.a];
    };

    Color.prototype.toRGBString = function() {
        return 'rgb(' + this.r + ',' + this.g + ',' + this.b + ')';
    };

    Color.prototype.toRGBAString = function() {
        return 'rgba(' + this.r + ',' + this.g + ',' +
                     this.b + ',' + this.a + ')';
    };

    Color.fromRGBString = function(str) {
        var matches = str.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        return new Color(matches[1], matches[2], matches[3]);
    };

    Color.prototype.toHexString = function() {
        return colorUtil.rgbToHex(this.toRGBArray());
    };

    Color.fromHexString = function(hex) {
        var normRgb = colorUtil.hexToRgb(hex);
        var denormRgb = colorUtil.denormalizeColor(normRgb);
        return new Color(denormRgb[0], denormRgb[1], denormRgb[2]);
    };

    return Color;

}]);
