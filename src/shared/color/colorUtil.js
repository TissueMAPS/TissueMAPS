angular.module('tmaps.shared.color')
.factory('colorUtil', function() {

    function rgbComponentToHex(c) {
        var hex = c.toString(16);
        return hex.length == 1 ? "0" + hex : hex;
    }

    return {
        /*
         * Utility function to convert between color representations.
         * TissueMAPS itself uses rgb colors with components between 0 and 1,
         * but other libs like highcharts want color components from 0 to 255.
         */
        denormalizeColor: function(normRgbColor) {
            return _.map(normRgbColor, function(component) {
                return Math.floor(component * 255);
            });
        },

        /*
         * Given a hex color string and a alpha value between 0 and 1, return
         * a rgba string that can be used with highcharts.
         */
        createRGBAfromHex: function(hex, alpha) {
            var rgb = this.hexToRgb(hex);
            var rgbDenorm = this.denormalizeColor(rgb);
            return 'rgba(' + rgbDenorm[0] + ', ' + rgbDenorm[1] + ', ' + rgbDenorm[2] + ', ' +  alpha + ')';
        },

        /*
         * Convert a hex string like '#ffffff' to a NORMALIZED RGB
         * color given as an array of numbers between 0 and 1.
         */
        hexToRgb: function(hex) {
            // Expand shorthand form (e.g. "03F") to full form (e.g. "0033FF")
            var shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
            hex = hex.replace(shorthandRegex, function(m, r, g, b) {
                return r + r + g + g + b + b;
            });

            var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
            return result ? [
                 parseInt(result[1], 16) / 255,
                 parseInt(result[2], 16) / 255,
                 parseInt(result[3], 16) / 255
            ] : null;
        },

        /*
         * Convert a color of the form [0.2, 0.3, 0.5] to its
         * corresponding hex representation.
         */
        rgbToHex: function(rgb) {
            return "#" + rgbComponentToHex(rgb[0] * 255) + rgbComponentToHex(rgb[1] * 255) + rgbComponentToHex(rgb[2] * 255);
        }
    };
});
