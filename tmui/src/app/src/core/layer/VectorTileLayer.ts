// Copyright (C) 2016-2018 University of Zurich.
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
interface VectorTileLayerOpts {
    url: string;
    size: Size;
    style?: ol.style.Style | ol.FeatureStyleFunction;
    visible?: boolean;
    strokeColor?: Color;
    fillColor?: Color;
}

/**
 * A vector layer that gets its openlayers features from tile requests sent to the
 * server.
 */
class VectorTileLayer extends BaseLayer<ol.layer.VectorTile> {

    private _fillColor: Color;
    private _strokeColor: Color;

    set fillColor(c: Color) {
        this._fillColor = c;
        this._olLayer.changed();
    }

    set strokeColor(c: Color) {
        this._strokeColor = c;
        this._olLayer.changed();
    }

    get fillColor() {
        return this._fillColor;
    }

    get strokeColor() {
        return this._strokeColor;
    }

    private _createDefaultStyleFunc() {
        // Currently a point can't have a stroke and can only
        // be colorized via a fill color.
        return (feature, style) => {
            var geomType = feature.getGeometry().getType();
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: this.fillColor.toOlColor()
                        }),
                        stroke: new ol.style.Stroke({
                            color: this.strokeColor.toOlColor(),
                        })
                    })
                ];
            } else if (geomType === 'Point') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: this.strokeColor.toOlColor()
                        })
                    })
                ];
            } else {
                throw new Error('Unknown geometry type for feature');
            }
        };
    }

    constructor(opt?: VectorTileLayerOpts) {
        super();

        var opt = opt === undefined ? <VectorTileLayerOpts> {} : opt;

        // Same extent as zoomify
        var extent = [0, -opt.size.height, opt.size.width, 0];

        // Compute the resolution array, i.e. an array of the number of tiles
        // per zoom level if the image was square.
        var imageWidth = opt.size.width;
        var imageHeight = opt.size.height;
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

        var vectorSource = new ol.source.VectorTile({
            url: opt.url,
            format: new ol.format.GeoJSON({
                defaultDataProjection: new ol.proj.Projection({
                    code: 'tm',
                    units: 'pixels',
                    extent: [0, 0, imageWidth, imageHeight]
                })
            }),
            tileGrid: new ol.tilegrid.TileGrid({
                extent: extent,
                minZoom: 0,
                tileSize: 256,
                resolutions: resolutions,
                origin: [0, 0]
            })
        });

        this._fillColor = opt.fillColor !== undefined ? opt.fillColor : Color.WHITE.withAlpha(0);
        this._strokeColor = opt.strokeColor !== undefined ? opt.strokeColor : Color.WHITE;

        this._olLayer = new ol.layer.VectorTile({
            source: vectorSource,
            visible: opt.visible,
            style: opt.style !== undefined ? opt.style : this._createDefaultStyleFunc()
        });
    }
}
