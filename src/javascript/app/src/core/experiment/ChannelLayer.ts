/// <reference path='../layer/ImageTileLayer.ts'/>
interface SerializedChannelLayer {
    id: string;
    tpoint: number;
    zplane: number;
    max_zoom: number;
    max_intensity: number;
    min_intensity: number;
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
    imageSize: Size;
    visible?: boolean;
}

class ChannelLayer extends ImageTileLayer {
    id: string;
    tpoint: number;
    zplane: number;
    maxIntensity: number;
    minIntensity: number;
    maxZoom: number;

    private _$stateParams: any;

    constructor(args: ChannelLayerArgs) {
        var _$stateParams = $injector.get<any>('$stateParams');
        var tileLayerArgs = {
            imageSize: args.imageSize,
            url: '/api/experiments/' + _$stateParams.experimentid +
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
        this.maxZoom = args.maxZoom;
    }
}
