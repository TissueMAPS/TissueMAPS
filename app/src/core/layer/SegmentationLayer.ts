/// <reference path='VisualTileLayer.ts'/>
/// <reference path='typedefs.ts'/>

interface SegmentationLayerOpts {
    t: number;
    zlevel: number;
    experimentId: string;
    imageWidth: number,
    imageHeight: number,
    visible?: boolean;
}

class SegmentationLayer extends VisualTileLayer {
    constructor(name: string, opt: SegmentationLayerOpts) {
        var url = '/api/experiments/' + opt.experimentId + '/mapobjects/cells?x={x}&y={y}&z={z}&t=' + opt.t + '&zlevel=' + opt.zlevel;
        var styleFunc = function(feature, style) {
            var geomType = feature.getGeometry().getType();
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: Color.GREEN.toOlColor()
                        }),
                        stroke: new ol.style.Stroke({
                            color: Color.WHITE.toOlColor()
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
        var options = <VisualTileLayerOpts>{};
        _.defaults(options, opt);
        _.defaults(options, {
            style: styleFunc,
            url: url
        });

        super(name, options);
    }
}


