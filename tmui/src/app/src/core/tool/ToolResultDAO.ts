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
interface SerializedPlot {
    id: string;
    type: string;
    attributes: any;
}

interface SerializedSegmentationLayer {
    id: string;
    experiment_id: string;
    image_size: any;
    tpoint: number;
    zplane: number;
}

interface SerializedToolResult {
    id: string;
    name: string;
    type: string;
    tool_name: string;
    attributes: any;
    submission_id: number;
    layers: SerializedSegmentationLayer[];
    plots: SerializedPlot[];
    experiment_id: string;
}

class ToolResultDAO extends HTTPDataAccessObject<ToolResult> {
    private _experimentId: string;

    constructor(experimentId: string) {
        // TODO: session
        super('/api/experiments/' + experimentId + '/tools/results')
        this._experimentId = experimentId;
    }

    fromJSON(data: SerializedToolResult) {
        return new ToolResult({
            id: data.id,
            submissionId: data.submission_id,
            name: data.name,
            tool: data.tool_name,
            layers: data.layers.map((layer) => {
                return this._createLabelLayer(layer, data)
            }),
            plots: data.plots.map((p) => {
                return this._createPlot(p);
            })
        });
    }

    private _createLabelLayer(layerArgs: SerializedSegmentationLayer, resultArgs: SerializedToolResult) {
        var labelLayerType = resultArgs.type.replace('ToolResult', 'LabelLayer');
        var LabelLayerClass = window[labelLayerType];
        if (LabelLayerClass !== undefined) {
            var layer = new LabelLayerClass({
                segmentationLayerId: layerArgs.id,
                name: resultArgs.name,
                attributes: resultArgs.attributes,
                tpoint: layerArgs.tpoint,
                zplane: layerArgs.zplane,
                size: layerArgs.image_size,
                experimentId: layerArgs.experiment_id
            });
            return layer;
        } else {
            throw new Error(
                'No client-side LabelLayer class found for tool: ' +
                resultArgs.type
            );
        }
    }

    private _createPlot(plot: SerializedPlot) {
        var PlotClass = window[plot.type];
        if (PlotClass !== undefined) {
            return new PlotClass({
                id: plot,
                attributes: plot.attributes
            });
        } else {
            throw new Error(
                'No client-side Plot class found that can handle' +
                ' plots of class: ' + plot.type
            );
        }
    }
}
