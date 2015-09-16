/// <reference path='TileLayer.ts'/>
class CycleLayer extends TileLayer {
    constructor(ol, $q: ng.IQService, opt: TileLayerArgs) {
        super(ol, $q, opt);
    }
}

class CycleLayerFactory {
    static $inject = ['openlayers', '$q'];
    constructor(private ol,
                private $q: ng.IQService) {}
    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: true,
            drawBlackPixels: true,
            drawWhitePixels: true
        });

        return new CycleLayer(this.ol, this.$q, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('cycleLayerFactory', CycleLayerFactory);

