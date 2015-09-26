/// <reference path='TileLayer.ts'/>
class OutlineLayer extends TileLayer {
    constructor(ol, $q: ng.IQService, colorFty: ColorFactory, opt: TileLayerArgs) {
        super(ol, $q, colorFty, opt);
    }
}

class OutlineLayerFactory {
    static $inject = ['openlayers', '$q', 'colorFactory']

    constructor(private ol,
                private $q: ng.IQService,
                private colorFty: ColorFactory) {}

    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: false,
            drawBlackPixels: false,
            drawWhitePixels: true
        });

        return new OutlineLayer(this.ol, this.$q, this.colorFty, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('outlineLayerFactory', OutlineLayerFactory);

