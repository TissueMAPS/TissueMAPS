/// <reference path='TileLayer.ts'/>
class OutlineLayer extends TileLayer {
    constructor(ol, opt: TileLayerArgs) {
        super(ol, opt);
    }
}

class OutlineLayerFactory {
    static $inject = ['openlayers']
    constructor(private ol) {}
    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: false,
            drawBlackPixels: false,
            drawWhitePixels: true
        });

        return new OutlineLayer(this.ol, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('OutlineLayerFactory', OutlineLayerFactory);

