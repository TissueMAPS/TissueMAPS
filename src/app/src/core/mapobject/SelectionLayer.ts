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
/// <reference path='../layer/VectorLayer.ts'/>

declare type SelectionId = number;

// FIXME: Deprecated. In the current state the markers are set directly via
// SelectionLayer.
class MarkerImageVisual extends Visual {
    // mapObjectMarkers: {};
    color: Color;

    constructor(position: MapPosition, color: Color) {
        // TODO: Maybe the size of the marker icon should be
        // changed according to the current resolution
        // var styleFunc = (feature: ol.Feature, resolution: number) => {
        //     var size = 42; // Compute via resolution
        //     // Avoid whitespaces in image name
        //     var colorRgbString = color.toRGBString().replace(/\s/g, '');
        //     var imageSrc =
        //         'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        //     var style = new ol.style.Style({
        //         image: new ol.style.Icon({
        //             // the bottom of the marker should point to the mapObject's
        //             // center
        //             anchor: [0.5, 0.9],
        //             src: imageSrc
        //         })
        //     });
        //     return [style];
        // };
        // var size = 42; // Compute via resolution
        // // Avoid whitespaces in image name
        // var colorRgbString = color.toRGBString().replace(/\s/g, '');
        // var imageSrc =
        //     'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        // var style = new ol.style.Style({
        //     image: new ol.style.Icon({
        //         // the bottom of the marker should point to the mapObject's
        //         // center
        //         anchor: [0.5, 0.9],
        //         src: imageSrc
        //     })
        // });
        var olFeature = new ol.Feature({
            // style: styleFunc,
            geometry: new ol.geom.Point([position.x, position.y])
        });

        super(olFeature);

        this.color = color;
    }
}

interface SelectionLayerOpts {
    color: Color;
    visible?: boolean;
}

class SelectionLayer extends VectorLayer {
    color: Color;
    name: string;

    constructor(name: string, opt: SelectionLayerOpts) {

        super({
            visible: opt.visible,
            zIndex: 100
        });

        this.name = name;

        this.color = opt.color;
        var size = 42; // Compute via resolution
        // Avoid whitespaces in image name
        var colorRgbString = this.color.toRGBString().replace(/\s/g, '');
        var imageSrc = 'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
        var style = new ol.style.Style({
            image: new ol.style.Icon({
                // the bottom of the marker should point to the mapObject's
                // center
                anchor: [0.5, 0.9],
                src: imageSrc
            })
        });

        this._olLayer.setStyle(style);
    }
}
