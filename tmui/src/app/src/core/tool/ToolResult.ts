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
interface ToolResultArgs {
    id: string;
    name: string;
    submissionId: number;
    layers: LabelLayer[];
    tool: string;
    plots: Plot[];
    visible?: boolean;
}

class ToolResult {

    id: string;
    submissionId: number;
    name: string;
    tool: string;
    layers: LabelLayer[];
    legend: Legend;
    plots: Plot[];

    private _visible: boolean;
    private _viewer: Viewer = null;

    get viewer() {
        return this._viewer;
    }

    get visible() {
        return this._visible;
    }

    set visible(doShow: boolean) {
        if (this.layers[0]) {
            this.layers[0].visible = doShow;
        }
        if (this.legend) {
            this.legend.visible = doShow;
        }
        this.plots.forEach((pl) => {
            pl.visible = doShow;
        });
        this._visible = doShow;
    }

    delete() {
        if (this.layers[0]) {
            this._viewer.viewport.removeLayer(this.layers[0]);
            // TODO: delete tool result
            // this._$http.delete()
        }
        if (this.legend) {
            this.legend.delete();
        }
    }

    /**
     * Construct a new ToolResult.
     *
     * @class ToolResult
     * @classdesc A tool result is basically a container for a labellayer as
     * well as potential plots. These results will show up in the interface as
     * tabs that can be marked as visible or invisible.
     * @param {ToolResultArgs} args - Constructor arguments.
     */
    constructor(args: ToolResultArgs) {
        this.id = args.id;
        this.name = args.name;
        this.layers = args.layers !== undefined ? args.layers : [];
        if (this.layers) {
            this.legend = this.layers[0].getLegend();
        } else {
            this.legend = null;
        }
        this.plots = args.plots !== undefined ? args.plots : [];
        this.visible = args.visible !== undefined ? args.visible : false;
        this.submissionId = args.submissionId;
    }

    attachToViewer(viewer: Viewer) {
        this._viewer = viewer;
        if (this.layers[0]) {
            this._viewer.viewport.addLayer(this.layers[0]);
            this.legend.attachToViewer(viewer);
        }
    }
}
