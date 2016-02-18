/// <reference path='Layer.ts'/>
/// <reference path='typedefs.ts'/>

interface SerializedTileLayer extends Serialized<TileLayer> {
      name: string;
      pyramidPath: string;
      imageSize: ImageSize;
      color: SerializedColor;
      additiveBlend: boolean;
      drawBlackPixels: boolean;
      drawWhitePixels: boolean;
      visible: boolean;
      brightness: number;
      min: number;
      max: number;
      opacity: number;
}

interface TileLayerArgs {
    name: string;
    imageSize: ImageSize;
    pyramidPath: string;

    additiveBlend?: string;
    drawBlackPixels?: boolean;
    drawWhitePixels?: boolean;
    visible?: boolean;
    color?: Color;
    brightness?: number;
    opacity?: number;
    min?: number;
    max?: number;
}

class TileLayer extends BaseLayer<ModifiedOlTileLayer> implements Serializable<TileLayer> {
    pyramidPath: string;
    imageSize: ImageSize;

    constructor(opt: TileLayerArgs) {
        super(opt.name);

        // Add trailing slash if not already present
        var pyramidPath = opt.pyramidPath;
        if (pyramidPath.substr(pyramidPath.length - 1) !== '/') {
            pyramidPath += '/';
        }
        this.pyramidPath = pyramidPath;
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
            drawBlackPixels: true,
            drawWhitePixels: true,
            visible: true
        });
        _olLayerArgs.color = _olLayerColor;

        _olLayerArgs.source = new ol.source.Zoomify({
            size: <ol.Size> this.imageSize,
            url: '/api' + pyramidPath,
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

    get opacity(): number {
        return this._olLayer.getOpacity();
    }

    set opacity(val: number) {
        this._olLayer.setOpacity(val);
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

    get drawBlackPixels(): boolean {
        return this._olLayer.getDrawBlackPixels();
    }

    set drawBlackPixels(val: boolean) {
        this._olLayer.setDrawBlackPixels(val);
    }

    get drawWhitePixels(): boolean {
        return this._olLayer.getDrawWhitePixels();
    }

    set drawWhitePixels(val: boolean) {
        this._olLayer.setDrawWhitePixels(val);
    }

    serialize() {
        return this.color.serialize().then((c) => {
            var $q = $injector.get<ng.IQService>('$q');
            return $q.when({
                name: this.name,
                pyramidPath: this.pyramidPath,
                imageSize: this.imageSize,
                color: c,
                additiveBlend: this.additiveBlend,
                drawBlackPixels: this.drawBlackPixels,
                drawWhitePixels: this.drawWhitePixels,
                visible: this.visible,
                brightness: this.brightness,
                min: this.min,
                max: this.max,
                opacity: this.opacity
            });
        });
    }

}
