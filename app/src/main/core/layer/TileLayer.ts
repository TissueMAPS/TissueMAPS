interface ITileLayer extends TileLayer {}
interface ICycleLayer extends ITileLayer {}
interface ICycleLayerFactory extends CycleLayerFactory {}
interface IOutlineLayer extends ITileLayer {}
interface IOutlineLayerFactory extends OutlineLayerFactory {}

type ImageSize = [number, number];

interface IModifiedOlTileLayer extends ol.layer.Tile {
    getMin(): number;
    setMin(val: number);
    getMax(): number;
    setMax(val: number);
    setColor(c: IColor);
    getColor(): IColor;
    setAdditiveBlend(b: boolean);
    getAdditiveBlend(): boolean;
    getDrawWhitePixels(): boolean;
    setDrawWhitePixels(b: boolean);
    getDrawBlackPixels(): boolean;
    setDrawBlackPixels(b: boolean);
}

interface ITileLayerArgs {
    name: string;
    imageSize: ImageSize;
    pyramidPath: string;
    color: IColor;
    additiveBlend: string;

    drawBlackPixels: boolean;
    drawWhitePixels: boolean;
    visible: boolean;

    brightness?: number;
    opacity?: number;
    min?: number;
    max?: number;
}

class TileLayer {
    name: string;
    pyramidPath: string;
    imageSize: ImageSize;
    blendMode: string;
    olLayer: IModifiedOlTileLayer;

    constructor(protected ol, opt: ITileLayerArgs) {
        this.name = opt.name;

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
        var olLayerArgs: any = _.defaults(opt, {
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

    /*
     * Draw the layer on the given openlayers map object
     */
     addToMap(olMap: ol.Map) {
         olMap.addLayer(this.olLayer);
     }

     /*
      * Remove the layer from the given openlayers map object
      */
      removeFromMap(olMap: ol.Map) {
          olMap.removeLayer(this.olLayer);
      }

      color(val?: IColor) {
          return angular.isDefined(val) ?
          this.olLayer.setColor(val) : this.olLayer.getColor();
      }

      opacity(val?: number) {
          return angular.isDefined(val) ?
          this.olLayer.setOpacity(val) : this.olLayer.getOpacity();
      }

      min(val?: number) {
          return angular.isDefined(val) ?
          this.olLayer.setMin(val) : this.olLayer.getMin();
      }

      max(val?: number) {
          return angular.isDefined(val) ?
          this.olLayer.setMax(val) : this.olLayer.getMax();
      }

      brightness(val?: number) {
          return angular.isDefined(val) ?
          this.olLayer.setBrightness(val) : this.olLayer.getBrightness();
      }

      visible(val?: boolean) {
          return angular.isDefined(val) ?
          this.olLayer.setVisible(val) : this.olLayer.getVisible();
      }

      additiveBlend(val?: boolean) {
          return angular.isDefined(val) ?
          this.olLayer.setAdditiveBlend(val) : this.olLayer.getAdditiveBlend();
      }

      drawBlackPixels(val?: boolean) {
          return angular.isDefined(val) ?
          this.olLayer.setDrawBlackPixels(val) : this.olLayer.getDrawBlackPixels();
      }

      drawWhitePixels(val?: boolean) {
          return angular.isDefined(val) ?
          this.olLayer.setDrawWhitePixels(val) : this.olLayer.getDrawWhitePixels();
      }
}

class TileLayerFactory {
    static $inject = ['openlayers'];
    constructor(private ol) {}
    create(opt: ITileLayerArgs) {
        return new TileLayer(this.ol, opt);
    }
}

