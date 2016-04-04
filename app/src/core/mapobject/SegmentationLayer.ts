/// <reference path='../layer/VectorTileLayer.ts'/>

interface SegmentationLayerOpts {
    t: number;
    zlevel: number;
    size: Size;
    experimentId: string;
    visible?: boolean;
}

class SegmentationLayer extends VectorTileLayer {

    objectTypeName: string;

    constructor(objectTypeName: string, opt: SegmentationLayerOpts) {
         
        var url = '/api/experiments/' + opt.experimentId + '/mapobjects/' +
                  objectTypeName + '?x={x}&y={y}&z={z}&t=' + opt.t + '&zlevel=' + opt.zlevel;
        super({
            visible: opt.visible,
            size: opt.size,
            url: url
        });

        this.objectTypeName = objectTypeName;
    }
}


