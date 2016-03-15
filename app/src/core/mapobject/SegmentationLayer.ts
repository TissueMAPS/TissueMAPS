interface SegmentationLayerOpts {
    t: number;
    zlevel: number;
    size: Size;
    experimentId: string;
    visible?: boolean;
}

class SegmentationLayer extends VisualTileLayer {

    objectName: string;

    constructor(objectName: string, opt: SegmentationLayerOpts) {
        this.objectName = objectName;
        var url = '/api/experiments/' + opt.experimentId + '/mapobjects/' +
                  objectName + '?x={x}&y={y}&z={z}&t=' + opt.t + '&zlevel=' + opt.zlevel;
        super(objectName, {
            visible: opt.visible,
            size: opt.size,
            url: url
        });
    }
}


