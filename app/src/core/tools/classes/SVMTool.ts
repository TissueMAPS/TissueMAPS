interface ClassResult {
    label: string;
    color: {r: number; g: number; b: number};
    cell_ids: string[];
}

interface ClassificationResult extends ToolResult {
    classes: ClassResult[];
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
            res.classes.forEach((cls) => {
                var color = Color.fromObject(cls.color);
                cls.cell_ids.forEach((id) => {
                    var cell = cellMap[id];
                    if (cell !== undefined) {
                        cells.push(cell.withFillColor(color));
                    }
                });
            });
            var layer = new ObjectLayer('SVM', {
                objects: cells
            });
            this.appInstance.viewport.addObjectLayer(layer);
        });
    }
}
