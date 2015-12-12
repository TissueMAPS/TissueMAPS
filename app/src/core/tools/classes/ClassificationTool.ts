type HexColorString = string;

/**
 * Classification server tools should use this structure
 * in for their response.
 */
interface ClassificationResult extends ToolResult {
    object_type: MapObjectType;
    predicted_labels: string[];
    object_ids: number[];
    colors: { [label:string]: HexColorString; };
}


abstract class ClassificationTool extends Tool {
    handleResult(res: ClassificationResult) {
        console.log(res);
        this.appInstance.mapObjectManager
        .getMapObjectsById(res.object_type, res.object_ids)
        .then((objs) => {
            var visuals = objs.map((o) => {
                var label = res.predicted_labels[o.id];
                var color = Color.fromHex(res.colors[label]);
                var visual = o.getVisual({
                    strokeColor: Color.BLACK.withAlpha(0),
                    fillColor: color
                });
                return visual;
            });
            var layer = new ResultLayer(this.name, {
                visuals: visuals
            });
            this.appInstance.viewport.addVisualLayer(layer);
            window['vp'] = this.appInstance.viewport;
        });
    }
}

