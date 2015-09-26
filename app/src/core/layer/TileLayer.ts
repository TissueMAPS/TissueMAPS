/// <reference path='Layer.ts'/>
/// <reference path='typedefs.ts'/>

interface SerializedTileLayer extends Serialized<TileLayer> {
      name: string;
      pyramidPath: string;
      imageSize: ImageSize;
      color: Color;
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

    color: Color;
    additiveBlend: string;
    drawBlackPixels: boolean;
    drawWhitePixels: boolean;
    visible: boolean;
    brightness?: number;
    opacity?: number;
    min?: number;
    max?: number;
}

class TileLayer extends Layer implements Serializable<TileLayer> {
    pyramidPath: string;
    imageSize: ImageSize;
    blendMode: string;
    olLayer: ModifiedOlTileLayer;

    constructor(protected ol,
                protected $q: ng.IQService,
                protected colorFty: ColorFactory,
                opt: TileLayerArgs) {
        super(opt.name);

        // Add trailing slash if not already present
        var pyramidPath = opt.pyramidPath;
        if (pyramidPath.substr(pyramidPath.length - 1) !== '/') {
            pyramidPath += '/';
        }
        this.pyramidPath = pyramidPath;

        this.imageSize = opt.imageSize;

        if (opt.additiveBlend) {
            this.blendMode = 'additive';
        } else {
            this.blendMode = 'normal';
        }

        // Some default properties
        var olLayerArgs: ModifiedOlTileLayerArgs = _.defaults(opt, {
            brightness: 0,
            opacity: 1,
            min: 0,
            max: 1
        });

        olLayerArgs.source = new ol.source.Zoomify({
            size: this.imageSize,
            url: '/api' + pyramidPath,
            crossOrigin: 'anonymous'
        });

        // Create the underlying openlayers layer object
        this.olLayer = new this.ol.layer.Tile(olLayerArgs);
    }

    color(val?: Color): Color {
        if (val) {
            this.olLayer.setColor(val.toNormalizedRGBArray());
            return val;
        } else {
            var arrayCol: number[] = this.olLayer.getColor();
            var col: Color = this.colorFty.createFromNormalizedRGBArray(arrayCol);
            return col;
        }
    }

    opacity(val?: number): number {
        if (angular.isDefined(val)) {
            this.olLayer.setOpacity(val);
            return val;
        } else {
            return this.olLayer.getOpacity();
        }
    }

    min(val?: number): number {
        if (angular.isDefined(val)) {
            this.olLayer.setMin(val);
            return val;
        } else {
            return this.olLayer.getMin();
        }
    }

    max(val?: number): number {
        if (angular.isDefined(val)) {
            this.olLayer.setMax(val);
            return val;
        } else {
            return this.olLayer.getMax();
        }
    }

    brightness(val?: number): number {
        if (angular.isDefined(val)) {
            this.olLayer.setBrightness(val);
            return val;
        } else {
            return this.olLayer.getBrightness();
        }
    }

    additiveBlend(val?: boolean): boolean {
        if (angular.isDefined(val)) {
            this.olLayer.setAdditiveBlend(val);
            return val;
        } else {
            return this.olLayer.getAdditiveBlend();
        }
    }

    drawBlackPixels(val?: boolean): boolean {
        if (angular.isDefined(val)) {
            this.olLayer.setDrawBlackPixels(val);
            return val;
        } else {
            return this.olLayer.getDrawBlackPixels();
        }
    }

    drawWhitePixels(val?: boolean): boolean {
        if (angular.isDefined(val)) {
            this.olLayer.setDrawWhitePixels(val);
            return val;
        } else {
            return this.olLayer.getDrawWhitePixels();
        }
    }

    serialize() {
        return this.$q.when({
            name: this.name,
            pyramidPath: this.pyramidPath,
            imageSize: this.imageSize,
            color: this.color(),
            additiveBlend: this.additiveBlend(),
            drawBlackPixels: this.drawBlackPixels(),
            drawWhitePixels: this.drawWhitePixels(),
            visible: this.visible(),
            brightness: this.brightness(),
            min: this.min(),
            max: this.max(),
            opacity: this.opacity()
        });
    }

}
