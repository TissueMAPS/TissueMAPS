/// <reference path='TileLayer.ts'/>
class ChannelLayer extends TileLayer {
    constructor(ol, $q: ng.IQService, opt: TileLayerArgs) {
        super(ol, $q, opt);
    }
}

class ChannelLayerFactory {
    static $inject = ['openlayers', '$q'];
    constructor(private ol,
                private $q: ng.IQService) {}
    create(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: true,
            drawBlackPixels: true,
            drawWhitePixels: true
        });

        return new ChannelLayer(this.ol, this.$q, tileLayerOptions);
    }
}

angular.module('tmaps.core.layer').service('channelLayerFactory', ChannelLayerFactory);

