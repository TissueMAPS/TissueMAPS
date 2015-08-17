angular.module('tmaps.core.layer')
.factory('CycleLayer', ['openlayers', 'TileLayer', function(ol, TileLayer) {

    function CycleLayer(options) {

        options.additiveBlend = true;
        options.drawBlackPixels = true;
        options.drawWhitePixels = true;

        TileLayer.call(this, options);
    }

    // Emulating classical inheritance like documented in:
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Inheritance_and_the_prototype_chain
    CycleLayer.prototype = Object.create(TileLayer.prototype);

    CycleLayer.prototype.toBlueprint = function() {
        return TileLayer.prototype.toBlueprint.call(this);
    };

    return CycleLayer;
}]);

