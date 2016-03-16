/// <reference path='Layer.ts'/>
/// <reference path='typedefs.ts'/>

interface SerializedTileLayer extends Serialized<TileLayer> {
      name: string;
      imageSize: Size;
      color: SerializedColor;
      additiveBlend: boolean;
      visible: boolean;
      brightness: number;
      min: number;
      max: number;
      opacity: number;
}

interface TileLayerArgs {
    channelId: string;
    name: string;
    imageSize: Size;

    additiveBlend?: string;
    visible?: boolean;
    color?: Color;
    brightness?: number;
    opacity?: number;
    min?: number;
    max?: number;
}

class TileLayer extends BaseLayer<ModifiedOlTileLayer> implements Serializable<TileLayer> {
    imageSize: Size;

    constructor(opt: TileLayerArgs) {
        super(opt.name);

        // Add trailing slash if not already present
        // var pyramidPath = opt.pyramidPath;
        // if (pyramidPath.substr(pyramidPath.length - 1) !== '/') {
        //     pyramidPath += '/';
        // }
        // this.pyramidPath = pyramidPath;
        this.imageSize = opt.imageSize;

        // Some default properties
        var _olLayerColor: number[];
        if (opt.color !== undefined) {
            _olLayerColor = opt.color.toNormalizedRGBArray();
        } else {
            _olLayerColor = [1, 1, 1];
        }

        var _olLayerArgs: ModifiedOlTileLayerArgs = _.defaults(opt, {
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
            url: '/api/channels/' + opt.channelId + '/tiles/',
            crossOrigin: 'anonymous'
        });

        // Create the underlying openlayers layer object
        this._olLayer = <ModifiedOlTileLayer> new ol.layer.Tile(_olLayerArgs);
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

    serialize() {
        return this.color.serialize().then((c) => {
            var $q = $injector.get<ng.IQService>('$q');
            return $q.when({
                name: this.name,
                imageSize: this.imageSize,
                color: c,
                additiveBlend: this.additiveBlend,
                visible: this.visible,
                brightness: this.brightness,
                min: this.min,
                max: this.max,
                opacity: this.opacity
            });
        });
    }

}
