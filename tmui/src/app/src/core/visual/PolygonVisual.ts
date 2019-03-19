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
type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

interface PolygonVisualOpts extends ColorizableOpts {
}

class PolygonVisual extends ColorizableVisual {

    constructor(outline: PolygonCoordinates, opts?: PolygonVisualOpts) {
        var outl: PolygonCoordinatesOL = [outline];
        var geom = new ol.geom.Polygon(outl);
        var feat = new ol.Feature({
            geometry: geom
        });

        var fillColor, strokeColor;
        if (opts && opts.fillColor) {
            fillColor = opts.fillColor.toOlColor();
        } else {
            fillColor = Color.RED.toOlColor();
        }
        if (opts && opts.strokeColor) {
            strokeColor = opts.strokeColor.toOlColor();
        } else {
            strokeColor = Color.WHITE.toOlColor();
        }

        var style = new ol.style.Style({
            fill: new ol.style.Fill({
                color: fillColor
            }),
            stroke: new ol.style.Stroke({
                color: strokeColor
            })
        });

        feat.setStyle(style);
        super(feat);
    }

    strokeColor: Color;
}
