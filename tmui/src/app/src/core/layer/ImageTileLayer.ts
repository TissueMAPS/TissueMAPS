// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
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

interface OlImageTileLayerArgs extends olx.layer.TileOptions {
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
      preload: number;
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
    preload?: number;
    min?: number;
    max?: number;
}

class ImageTileLayer extends BaseLayer<OlImageTileLayer> {
    imageSize: Size;

    constructor(args: ImageTileLayerArgs) {
        super();

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

        var url = args.url;
        if (url.match(/\/$/) === null) {
            url += '/';
        }
        url += 'tiles?x={x}&y={y}&z={z}';

        var imageSource = new ol.source.TileImage({
            url: url,
            crossOrigin: 'anonymous',
            projection: null,
            tileGrid: new ol.tilegrid.TileGrid({
                extent: extent,
                minZoom: 0,
                tileSize: 256,
                resolutions: resolutions,
                origin: [0, 0]
            }),
            tileClass: ol.source.NonsquaredTile
        });

        var olLayerArgs = {
            brightness: args.brightness !== undefined ? args.brightness : 0,
            opacity: args.opacity !== undefined ? args.opacity : 1,
            preload: args.preload !== undefined ? args.preload : 0,
            min: args.min !== undefined ? args.min : 0,
            max: args.max !== undefined ? args.max : 1,
            additiveBlend: args.additiveBlend !== undefined ? args.additiveBlend : false,
            visible: args.visible !== undefined ? args.visible : true,
            color: args.color !== undefined ? args.color.toNormalizedRGBArray() : [1, 1, 1],
            // preload: Infinity,
            source: imageSource
        }

        // Create the underlying openlayers layer object
        this._olLayer = <OlImageTileLayer> new ol.layer.Tile(olLayerArgs);
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


