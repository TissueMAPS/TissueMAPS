type HexColorString = string;

/**
 * Classification server tools should use this structure
 * in for their response.
 */
interface ClassificationResultPayload {
    classification_result_id: number;
}

abstract class ClassifierToolSession extends ToolSession {
    handleResult(res: ClassificationResultPayload) {
        console.log('Called handleResult of ClassificationTool');
        console.log(res);
        // this.appInstance.mapObjectRegistry
        // .getMapObjectsById(res.object_type, res.object_ids)
        // .then((objs) => {
        //     var visuals = objs.map((o) => {
        //         var label = res.predicted_labels[o.id];
        //         var color = Color.fromHex(res.colors[label]);
        //         var visual = o.getVisual({
        //             strokeColor: Color.BLACK.withAlpha(0),
        //             fillColor: color
        //         });
        //         return visual;
        //     });
        //     // var layer = new ResultLayer(this.name, {
        //     //     visuals: visuals
        //     // });
        //     // this.appInstance.viewport.addVisualLayer(layer);
        // });
    }
}

