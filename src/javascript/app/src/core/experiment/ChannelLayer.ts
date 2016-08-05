/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    max_zoom: number;
    max_intensity: number;
    min_intensity: number;
    experiment_id: string;
    image_size: {
        width: number;
        height: number;
    };
}

interface ChannelLayerArgs {
    id: string;
    tpoint: number;
    zplane: number;
    maxZoom: number;
    maxIntensity: number;
    minIntensity: number;
    experimentId: string;
    imageSize: Size;
    visible?: boolean;
}

class ChannelLayer extends ImageTileLayer {
    id: string;
    tpoint: number;
    zplane: number;
    maxIntensity: number;
    minIntensity: number;
    experimentId: string;
    maxZoom: number;

    constructor(args: ChannelLayerArgs) {

        var tileLayerArgs = {
            imageSize: args.imageSize,
            url: '/api/experiments/' + args.experimentId +
                '/channel_layers/' + args.id + '',
            additiveBlend: true,
            visible: args.visible
        };
        super(tileLayerArgs);

        this.id = args.id;
        this.tpoint = args.tpoint;
        this.zplane = args.zplane;
        this.maxIntensity = args.maxIntensity;
        this.minIntensity = args.minIntensity;
        this.experimentId = args.experimentId;
        this.maxZoom = args.maxZoom;
    }
}
