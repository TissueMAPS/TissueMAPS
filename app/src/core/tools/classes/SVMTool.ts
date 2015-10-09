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
        res.classes.forEach((cls) => {
            this.appInstance.experiment.cellMap.then((cellMap) => {
                var color = Color.createFromObject(cls.color);
                var cells = _(cls.cell_ids).map((id) => {
                    return cellMap[id];
                });
                console.log(cells);
                var layer = new ObjectLayer(cls.label, {
                    objects: cells,
                    fillColor: null,
                    strokeColor: color
                });
                this.appInstance.viewport.addObjectLayer(layer);
            });
        });
    }
}
