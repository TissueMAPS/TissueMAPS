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
        var imageWidth = args.imageSize.width;
        var imageHeight = args.imageSize.height;
        var extent = [0, -imageHeight, imageWidth, 0];

        // Compute the resolution array, i.e. an array of the number of tiles
        // per zoom level if the image was square.
        var tileSizeIter = 256;
        var i = 1;
        var resolutions = [1];
        while (imageWidth > tileSizeIter || imageHeight > tileSizeIter) {
            tileSizeIter *= 2;
            i *= 2;
            resolutions.push(i);
        }
        // e.g. [1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1] for maxzoom == 10
        resolutions = resolutions.reverse();

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

        var url = args.url;
        if (url.match(/\/$/) === null) {
            url += '/';
        }

        // ZOOMIFY
        // var imageSourceZoomify = new ol.source.Zoomify({
        //     size:  [this.imageSize.width, this.imageSize.height],
        //     url: url + 'tiles/',
        //     crossOrigin: 'anonymous'
        // });

        //// TILE IMAGE
        url += 'tiles?x={x}&y={y}&z={z}';
        var imageSource = new ol.source.TileImage({
            url: url,
            // tileUrlFunction: function(tileCoord, pixelRatio, proj) {
            //     var z = tileCoord[0];
            //     var x = tileCoord[1];
            //     var y = -tileCoord[2]-1;
            //     console.log('Image:', z, x, y);
            //     var st = window['map'].getView().getState();
            //     console.log('Center:', st.center);
            //     console.log('Res:', st.resolution);
            //     // return url + 'image?z=' + z + '&x=' + x + '&y=' + y;
            //     return url.replace(/{x}/, x.toString())
            //               .replace(/{y}/, y.toString())
            //               .replace(/{z}/, z.toString());
            // },
            crossOrigin: 'anonymous',
            projection: null,
            tileGrid: new ol.tilegrid.TileGrid({
                extent: extent,
                minZoom: 0,
                tileSize: 256,
                resolutions: resolutions,
                origin: [0, 0]
            }),
            // The zoomify tile allows for non-square image tiles.
            // If a loaded image isn't square, the image is first drawn onto a square
            // transparent canvas and this canvas is then used as the tile image.
            tileClass: ol.source['ZoomifyTile_']
        });
        
        // _olLayerArgs.source = imageSourceZoomify;
        _olLayerArgs.source = imageSource;

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
