angular.module('tmaps.core.layer')
.factory('TileLayer', ['openlayers', function(ol) {

    /**
     * Create a tmaps tilelayer object that wraps a openlayers layer object
     * and provides some other functionality specific to tmaps.
     */
    function TileLayer(options) {
        // Options specific to the tmaps wrapper of the openlayers layer
        if (_.isUndefined(options.name))
            throw 'TileLayer needs the name of the pyramid image!';
        if (_.isUndefined(options.imageSize))
            throw 'TileLayer needs the size of the pyramid image!';
        if (_.isUndefined(options.pyramidPath))
            throw 'TileLayer needs the path of the pyramid image!';

        this.name = options.name;
        // Add trailing slash if not already present
        var pyramidPath = options.pyramidPath;
        if (pyramidPath.substr(pyramidPath.length - 1) !== '/') {
            pyramidPath += '/';
        }
        this.pyramidPath = pyramidPath;
        this.imageSize = options.imageSize;

        // Options forwarded to the underlying openlayers layer
        if (_.isUndefined(options.color))
            throw 'TileLayer needs an initial color of the form [1.0, 0, 0]';
        if (_.isUndefined(options.additiveBlend))
            throw 'TileLayer needs to know wether to blend the layer additively!';
        if (_.isUndefined(options.drawBlackPixels))
            throw 'TileLayer needs to know wether to draw black pixels!';
        if (_.isUndefined(options.drawWhitePixels))
            throw 'TileLayer needs to know wether to draw white pixels!';
        if (_.isUndefined(options.visible))
            throw 'TileLayer needs to know wether to draw the layer!';

        if (options.additiveBlend) {
            this.blendMode = 'additive';
        } else {
            this.blendMode = 'normal';
        }

        // Some default properties
        options = _.defaults(options, {
            brightness: 0,
            opacity: 1,
            min: 0,
            max: 1
        });

        options.source = new ol.source.Zoomify({
            size: options.imageSize,
            url: '/api' + pyramidPath,
            crossOrigin: 'anonymous'
        });

        // Create the underlying openlayers layer object
        this.olLayer = new ol.layer.Tile(options);
    }

    /*
     * Draw the layer on the given openlayers map object
     */
    TileLayer.prototype.addToMap = function(olMap) {
        var self = this;

        /*
         * Currently the additive rendering and multiplication with
         * colors is done in the hacked openlayers source code, but this
         * could just as well be done with the following code.
         * One thing that still has to be done via a custom shader
         * is the adjustment of contrast.
         * Still, it may be useful at some point to remove all the unneeded
         * hacks from the OL source and include the functionality
         * via these compose-event listeners.
         */
        // if (this.blendMode === 'additive') {
        //     var gl = $('canvas').get(0).getContext('webgl');

        //     this.olLayer.on('precompose', function(evt) {
        //         var color = self.olLayer.getColor();
        //         gl.blendEquation(gl.FUNC_ADD);
        //         gl.blendColor(color[0], color[1], color[2], 1);
        //         // Multiply source pixels (i.e. pixels of this layer)
        //         // component-wide with a constant color and then
        //         // add it to destination pixels that are just multiplied with 1.
        //         gl.blendFunc(gl.CONSTANT_COLOR, gl.ONE);
        //         // evt.context.globalCompositeOperation = 'lighter'; // canvas
        //     });

        //     this.olLayer.on('postcompose', function(evt) {
        //         // Set back to default
        //         gl.blendFuncSeparate(
        //             gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA,
        //             gl.ONE, gl.ONE_MINUS_SRC_ALPHA
        //         );
        //         // evt.context.globalCompositeOperation = 'source-over';
        //     });
        // }

        olMap.addLayer(this.olLayer);
    };

    /*
     * Remove the layer from the given openlayers map object
     */
    TileLayer.prototype.removeFromMap = function(olMap) {
        olMap.removeLayer(this.olLayer);
    };

    /*
     * Angular-style getter & setters for the properties of the OL Layer.
     */
    TileLayer.prototype.color = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setColor(val) : this.olLayer.getColor();
    };

    TileLayer.prototype.opacity = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setOpacity(val) : this.olLayer.getOpacity();
    };

    TileLayer.prototype.min = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setMin(val) : this.olLayer.getMin();
    };

    TileLayer.prototype.max = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setMax(val) : this.olLayer.getMax();
    };

    TileLayer.prototype.brightness = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setBrightness(val) : this.olLayer.getBrightness();
    };

    TileLayer.prototype.visible = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setVisible(val) : this.olLayer.getVisible();
    };

    TileLayer.prototype.additiveBlend = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setAdditiveBlend(val) : this.olLayer.getAdditiveBlend();
    };

    TileLayer.prototype.drawBlackPixels = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setDrawBlackPixels(val) : this.olLayer.getDrawBlackPixels();
    };

    TileLayer.prototype.drawWhitePixels = function(val) {
        return angular.isDefined(val) ?
            this.olLayer.setDrawWhitePixels(val) : this.olLayer.getDrawWhitePixels();
    };

    TileLayer.prototype.toBlueprint = function() {
        return {
            name: this.name,
            pyramidPath: this.pyramidPath,
            imageSize: this.imageSize,
            color: this.color(),
            additiveBlend: this.additiveBlend(),
            drawBlackPixels: this.drawBlackPixels(),
            drawWhitePixels: this.drawWhitePixels(),
            visible: this.visible(),
            brightness: this.brightness(),
            min: this.min(),
            max: this.max(),
            opacity: this.opacity()
        };
    };

    return TileLayer;

}]);

