/// <reference path='../layer/VectorTileLayer.ts'/>

interface SegmentationLayerOpts {
    tpoint: number;
    zplane: number;
    size: Size;
    experimentId: string;
    visible?: boolean;
}

class SegmentationLayer extends VectorTileLayer {

    objectTypeName: string;

    /**
     * Construct a SegmentationLayer.
     * @classdesc A layer showing outlines for a specific mapobject type.
     */
    constructor(objectTypeName: string, opt: SegmentationLayerOpts) {
         
        var url = '/api/experiments/' + opt.experimentId + '/mapobjects/' +
                  objectTypeName + '/tile'
                  '?x={x}&y={y}&z={z}' + '&zplane=' + opt.zplane + '&tpoint=' + opt.tpoint;
        super({
            visible: opt.visible,
            size: opt.size,
            url: url,
            strokeColor: Color.WHITE,
            fillColor: Color.WHITE.withAlpha(0),
        });

        this.objectTypeName = objectTypeName;
    }
}


