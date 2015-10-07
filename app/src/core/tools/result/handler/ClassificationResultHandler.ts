interface CellClassificationResult {
    classes: Array<{classLabel: CellId; }>
}

class CellClassificationResultHandler implements ToolResultHandler {
    handle(res) {
        console.log(res);
    }
}
