/// <reference path='TileLayer.ts'/>
class ChannelLayer extends TileLayer {
    constructor(ol, $q: ng.IQService, colorFty: ColorFactory, opt: TileLayerArgs) {
        super(ol, $q, colorFty, opt);
    }
}

class ChannelLayerFactory {
    static $inject = ['openlayers', '$q', 'colorFactory'];
    constructor(private ol,
                private $q: ng.IQService,
                private colorFactory: ColorFactory) {}

    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: true,
            drawBlackPixels: true,
            drawWhitePixels: true
        });

        return new ChannelLayer(this.ol, this.$q, this.colorFactory, tileLayerOptions);
    }
}

angular.module('tmaps.core').service('channelLayerFactory', ChannelLayerFactory);

