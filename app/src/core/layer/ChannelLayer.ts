/// <reference path='TileLayer.ts'/>
class ChannelLayer extends TileLayer {
    constructor(opt: TileLayerArgs) {
        var tileLayerOptions = _.defaults(opt, {
            additiveBlend: true,
            drawBlackPixels: true,
            drawWhitePixels: true
        });
        super(tileLayerOptions);
    }
}
