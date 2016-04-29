/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    max_zoom: number;
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
    maxZoom: number;

    constructor(args: ChannelLayerArgs) {
        
        var tileLayerArgs = {
            imageSize: args.image_size,
            url: '/api/channel_layers/' + args.id + '',
            additiveBlend: true
        };
        super(tileLayerArgs);

        this.id = args.id;
        this.tpoint = args.tpoint;
        this.zplane = args.zplane;
        this.maxZoom = args.max_zoom;
    }
}
