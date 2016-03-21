/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    image_size: {
        width: number;
        height: number;
    };
}

type ChannelLayerArgs = SerializedChannelLayer;

class ChannelLayer extends ImageTileLayer {
    id: string;
    tpoint: number;
    zplane: number;

    constructor(args: ChannelLayerArgs) {
        this.id = args.id;
        this.tpoint = args.tpoint;
        this.zplane = args.zplane;

        var tileLayerArgs = {
            imageSize: args.image_size,
            url: '/api/channel_layers/' + this.id + '/tiles/',
            additiveBlend: true
        };
        super(tileLayerArgs);
    }
}
