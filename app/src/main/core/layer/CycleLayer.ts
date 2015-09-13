/// <reference path='TileLayer.ts'/>
class CycleLayer extends TileLayer {
    constructor(ol, opt: TileLayerArgs) {
        super(ol, opt);
    }
}

class CycleLayerFactory {
    static $inject = ['openlayers'];
    constructor(private ol) {}
    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: true,
            drawBlackPixels: true,
            drawWhitePixels: true
        });

        return new CycleLayer(this.ol, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('CycleLayerFactory', CycleLayerFactory);

