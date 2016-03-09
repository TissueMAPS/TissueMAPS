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
        var styleFunc = function(feature, style) {
            var geomType = feature.getGeometry().getType();
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: Color.GREEN.withAlpha(0).toOlColor()
                        }),
                        stroke: new ol.style.Stroke({
                            color: Color.GREEN.toOlColor(),
                        })
                    })
                ];
            } else if (geomType === 'Point') {
                return [
                    new ol.style.Style({
                        image: new ol.style.Circle({
                            fill: new ol.style.Fill({
                                color: [0, 255, 0, 1]
                            }),
                            radius: 2
                        })
                    })
                ];
            } else {
                throw new Error('Unknown geometry type for feature');
            }
        };
        super(objectName, {
            visible: opt.visible,
            size: opt.size,
            style: styleFunc,
            url: url
        });
    }
}


