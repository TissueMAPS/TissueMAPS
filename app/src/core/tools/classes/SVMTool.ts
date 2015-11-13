interface ClassificationResult extends ToolResult {
    predicted_labels: string[];
    colors: { [label:string]: {r: number, g: number, b: number}; };
    cell_ids: number[];
}

class SVMTool extends Tool {
    constructor(appInstance: AppInstance) {
        super(
            appInstance,
            'SVM',
            'SVM Classifier',
            'Classify cells using a Support Vector Machine',
            '/templates/tools/modules/SVM/svm.html',
            'SVM',
            1025,
            450
          )
    }

    handleResult(res: ClassificationResult) {
        this.appInstance.experiment.cellMap.then((cellMap) => {
            var cells = [];
            var i;
            var nCells = res.cell_ids.length;
            for (i = 0; i < nCells; i++) {
                var id = res.cell_ids[i]
                var cell = cellMap[id];
                if (cell !== undefined) {
                    var label = res.predicted_labels[i];
                    var color = res.colors[label];
                    cells.push(cell.withFillColor(Color.fromObject(color)));
                }
            }
            var layer = new ObjectLayer('SVM', {
                objects: cells
            });
            this.appInstance.viewport.addObjectLayer(layer);
        });
    }
}
