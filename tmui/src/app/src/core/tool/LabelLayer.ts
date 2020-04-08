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
/**
 * A function that maps a mapobject label to some color.
 */
interface LabelColorMapper {
    (label: any): Color;
}

// TODO: segmentation layer and tool result id
interface LabelLayerArgs {
    segmentationLayerId: string;
    name: string;
    attributes: any;
    tpoint: number;
    zplane: number;
    visible?: boolean;
    size: Size;
}

abstract class LabelLayer extends VectorTileLayer {

    segmentationLayerId: string;
    attributes: any;

    private _colorMapper: LabelColorMapper;

    /**
     * Each specific implmentation of a LabelLayer should provide a function
     * that maps labels that were given to mapobjects by some tool to a
     * specific color.
     */
    abstract getLabelColorMapper(): LabelColorMapper;

    /**
     * Each specific implementation of a LabelLayer can provide a legend that
     * is displayed beside the layer and that explains how the colors are to be
     * interpreted.
     */
    abstract getLegend(): Legend;
    private _$stateParams: any;

    /**
     * It's important that the getLabelColorMapper() method is only called
     * once since constructing the colorMapper might be an expensive operation.
     */
    get colorMapper() {
        if (this._colorMapper === undefined) {
            this._colorMapper = this.getLabelColorMapper();
        }
        return this._colorMapper;
    }

    /**
     * Construct an object of type LabelLayer.
     * @class LabelLayerArgs
     * @classdesc A LabelLayer is a type of layer that will request its vector
     * features from the server. This layer type is similar to a SegmentationLayer.
     * However, in contrast to a standard SegmentationLayer, the features that
     * are sent by the server contain a 'label' attribute that is set to the
     * label that the original tool assigned to the respective mapobject.
     * Each polygon/point is colored according to this label.
     */
    constructor(args: LabelLayerArgs) {
        var styleFunc = (feature, style) => {
            var geomType = feature.getGeometry().getType();
            var label = feature.get('label');
            var fillColor: ol.Color;
            if (label == "None") {
                fillColor = '#40000000'
            } else {
                fillColor = this.colorMapper(label).toOlColor();
            }
            if (geomType === 'Polygon' || geomType === 'Point') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: fillColor
                        })
                    })
                ];
            } else {
                throw new Error('Unknown geometry type for feature');
            }
        };
        var _$stateParams = $injector.get<any>('$stateParams');
        var url = '/api/experiments/' + _$stateParams.experimentid +
            '/segmentation_layers/' + args.segmentationLayerId +
            '/labeled_tiles?x={x}&y={y}&z={z}' +
            '&result_name=' + args.name

        super({
            style: styleFunc,
            url: url,
            visible: args.visible,
            size: args.size
        });

        this.segmentationLayerId = args.segmentationLayerId;
        this.attributes = args.attributes;
    }
}
