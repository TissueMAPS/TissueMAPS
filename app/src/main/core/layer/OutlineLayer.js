angular.module('tmaps.core.layer')
.factory('OutlineLayer', ['openlayers', 'TileLayer', function(ol, TileLayer) {

    function OutlineLayer(options) {

        _.defaults(options, {
            additiveBlend: false,
            drawBlackPixels: false,
            drawWhitePixels: true
        });

        TileLayer.call(this, options);
    }

    // Emulating classical inheritance like documented in:
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Inheritance_and_the_prototype_chain
    OutlineLayer.prototype = Object.create(TileLayer.prototype);

    OutlineLayer.prototype.toBlueprint = function() {
        return TileLayer.prototype.toBlueprint.call(this);
    };

    return OutlineLayer;
}]);


