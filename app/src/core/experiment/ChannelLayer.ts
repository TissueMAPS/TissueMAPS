/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    imageSize: {
        width: number;
        height: number;
    };
}

type ChannelLayerArgs = SerializedChannelLayer;

class ChannelLayer extends ImageTileLayer {
    id: string;
    tpoint: number;
    zplane: number;
    imageSize: Size;

    constructor(args: ChannelLayerArgs) {
        this.id = args.id;
        this.tpoint = args.tpoint;
        this.zplane = args.zplane;
        this.imageSize = args.imageSize;

        var tileLayerArgs = _.defaults(args, {
            additiveBlend: true,
            url: '/api/channel_layers/' + this.id + '/tiles/',
        });
        super(tileLayerArgs);
    }
}
