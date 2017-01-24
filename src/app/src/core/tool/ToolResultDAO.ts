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
interface SerializedPlot {
    id: string;
    type: string;
    attributes: any;
}

interface SerializedToolResult {
    id: string;
    name: string;
    type: string;
    attributes: any;
    submission_id: number;
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
            layer: this._createLabelLayer(data),
            plots: data.plots.map((p) => {
                return this._createPlot(p);
            })
        });
    }

    private _createLabelLayer(result: SerializedToolResult) {
        // TODO: tpoint and zplane
        var labelLayerType = result.type;
        var LabelLayerClass = window[labelLayerType];
        if (LabelLayerClass !== undefined) {
            return new LabelLayerClass({
                id: result.id,
                name: result.name,
                attributes: result.attributes,
                tpoint: 0,
                zplane: 0,
                experimentId: this._experimentId
            });
        } else {
            throw new Error(
                'No client-side LabelLayer class found that can handle' +
                ' layers of class: ' + result.type
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
