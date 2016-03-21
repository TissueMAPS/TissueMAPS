/// <reference path='Layer.ts'/>
interface OlImageTileLayer extends ol.layer.Tile {
    getMin(): number;
    setMin(val: number);
    getMax(): number;
    setMax(val: number);
    setColor(c: number[]);
    getColor(): number[];
    setAdditiveBlend(b: boolean);
    getAdditiveBlend(): boolean;
}

interface OlImageTileLayerArgs extends olx.layer.LayerOptions {
    color?: number[];  // for example: [1, 0, 0] == red
    additiveBlend?: boolean;
    min?: number;
    max?: number;
}

interface SerializedImageTileLayer extends Serialized<ImageTileLayer> {
      imageSize: Size;
      color: SerializedColor;
      additiveBlend: boolean;
      visible: boolean;
      brightness: number;
      min: number;
      max: number;
      opacity: number;
}

interface ImageTileLayerArgs {
    imageSize: Size;
    url: string;

    additiveBlend?: boolean;
    visible?: boolean;
    color?: Color;
    brightness?: number;
    opacity?: number;
    min?: number;
    max?: number;
}

class ImageTileLayer extends BaseLayer<OlImageTileLayer> {
    imageSize: Size;

    constructor(args: ImageTileLayerArgs) {
        super();

        // Add trailing slash if not already present
        // var pyramidPath = args.pyramidPath;
        // if (pyramidPath.substr(pyramidPath.length - 1) !== '/') {
        //     pyramidPath += '/';
        // }
        // this.pyramidPath = pyramidPath;
        this.imageSize = args.imageSize;

        // Some default properties
        var _olLayerColor: number[];
        if (args.color !== undefined) {
            _olLayerColor = args.color.toNormalizedRGBArray();
        } else {
            _olLayerColor = [1, 1, 1];
        }

        var _olLayerArgs: OlImageTileLayerArgs = _.defaults(args, {
            brightness: 0,
            opacity: 1,
            min: 0,
            max: 1,
            additiveBlend: true,
            visible: true
        });
        _olLayerArgs.color = _olLayerColor;

        _olLayerArgs.source = new ol.source.Zoomify({
            size:  [this.imageSize.width, this.imageSize.height],
            url: args.url,
            crossOrigin: 'anonymous'
        });

        // Create the underlying openlayers layer object
        this._olLayer = <OlImageTileLayer> new ol.layer.Tile(_olLayerArgs);
    }

    get color(): Color {
        var arrayCol: number[] = this._olLayer.getColor();
        var col: Color = Color.fromNormalizedRGBArray(arrayCol);
        return col;
    }

    set color(val: Color) {
        if (val !== null) {
            var newCol = val.toNormalizedRGBArray();
            this._olLayer.setColor(newCol);
        } else {
            this._olLayer.setColor(null);
        }
    }

    get min(): number {
        return this._olLayer.getMin();
    }

    set min(val: number) {
        this._olLayer.setMin(val);
    }

    get max(): number {
        return this._olLayer.getMax();
    }

    set max(val: number) {
        this._olLayer.setMax(val);
    }

    get brightness(): number {
        return this._olLayer.getBrightness();
    }

    set brightness(val: number) {
        this._olLayer.setBrightness(val);
    }

    get additiveBlend(): boolean {
        return this._olLayer.getAdditiveBlend();
    }

    set additiveBlend(val: boolean) {
        this._olLayer.setAdditiveBlend(val);
    }

    // serialize() {
    //     return this.color.serialize().then((c) => {
    //         var $q = $injector.get<ng.IQService>('$q');
    //         return $q.when({
    //             imageSize: this.imageSize,
    //             color: c,
    //             additiveBlend: this.additiveBlend,
    //             visible: this.visible,
    //             brightness: this.brightness,
    //             min: this.min,
    //             max: this.max,
    //             opacity: this.opacity
    //         });
    //     });
    // }

}
