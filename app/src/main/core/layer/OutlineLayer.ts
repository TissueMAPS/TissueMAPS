/// <reference path='TileLayer.ts'/>
class OutlineLayer extends TileLayer {
    constructor(ol, $q, opt: TileLayerArgs) {
        super(ol, $q, opt);
    }
}

class OutlineLayerFactory {
    static $inject = ['openlayers', '$q']

    constructor(private ol,
                private $q) {}

    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: false,
            drawBlackPixels: false,
            drawWhitePixels: true
        });

        return new OutlineLayer(this.ol, this.$q, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('OutlineLayerFactory', OutlineLayerFactory);

