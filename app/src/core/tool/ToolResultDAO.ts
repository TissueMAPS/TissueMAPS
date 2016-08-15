interface SerializedPlot {
    id: string;
    type: string;
    attributes: any;
}

interface SerializedLabelLayer {
    id: string;
    name: string;
    type: string;
    attributes: any;
    experiment_id: string;
}

interface SerializedToolResult {
    id: string;
    name: string;
    layer: SerializedLabelLayer;
    plots: SerializedPlot[];
    experiment_id: string;
}

class ToolResultDAO extends HTTPDataAccessObject<ToolResult> {
    constructor(experimentId: string) {
        // TODO: session
        super('/api/experiments/' + experimentId + '/tools/results')
    }

    fromJSON(data: SerializedToolResult) {
        return new ToolResult({
            id: data.id,
            name: data.name,
            layer: this._createLabelLayer(data.layer),
            plots: data.plots.map((p) => {
                return this._createPlot(p);
            })
        });
    }

    private _createLabelLayer(layer: SerializedLabelLayer) {
        var labelLayerType = layer.type;
        var LabelLayerClass = window[labelLayerType];
        if (LabelLayerClass !== undefined) {
            return new LabelLayerClass({
                id: layer.id,
                name: layer.name,
                attributes: layer.attributes,
                tpoint: 0,
                zplane: 0
            });
        } else {
            throw new Error(
                'No client-side LabelLayer class found that can handle' +
                ' layers of class: ' + layer.type
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
