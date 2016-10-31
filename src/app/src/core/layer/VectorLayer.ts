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
/**
 * Optional arguments for the VectorLayer constructor.
 */
interface VectorLayerArgs {
    visuals?: Visual[];
    visible?: boolean;
    zIndex?: number;
}

/**
 * Layer class for Visuals, i.e. visualizable objects like marker symbols
 * or single outlines that highlight a specific cell.
 * This is a wrapper around an openlayers vector layer.
 */
class VectorLayer extends BaseLayer<ol.layer.Vector> {

    private _visuals: Visual[] = [];

    constructor(args: VectorLayerArgs = {}) {
        super();

        var vectorSource = new ol.source.Vector({
            features: []
        });

        this._olLayer = new ol.layer.Vector({
            source: vectorSource,
            visible: args.visible === undefined ? true : false,
            zIndex: args.zIndex
        });

        if (args.visuals !== undefined) {
            this.addVisuals(args.visuals);
        }
    }

    get visuals() {
        return this._visuals;
    }

    addVisual(v: Visual) {
        if (v !== undefined && v !== null) {
            this._visuals.push(v);
            var src = this._olLayer.getSource();
            var feat = v.olFeature
            src.addFeature(feat);
        } else {
            console.log('Warning: trying to add undefined or null Visual.');
        }
    }

    addVisuals(vs: Visual[]) {
        var visuals = [];
        vs.forEach((v) => {
            if (v !== undefined && v !== null) {
                visuals.push(v);
            } else {
                console.log('Warning: trying to add undefined or null Visual.');
            }
        });
        visuals.forEach((v) => {
            this._visuals.push(v);
        });
        var features = _(visuals).map((v) => {
            var feat = v.olFeature;
            return feat;
        });
        this._olLayer.getSource().addFeatures(features);
    }

    removeVisual(v: Visual) {
        var src = this._olLayer.getSource();
        src.removeFeature(v.olFeature);
    }
}
