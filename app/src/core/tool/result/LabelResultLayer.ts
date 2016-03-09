interface LabelResultLayerOpts {
    labelResultId: number;
    t: number;
    zlevel: number;
    size: Size;
    visible?: boolean;
}


class LabelResultLayer extends VisualTileLayer {
    constructor(name: string, opt: LabelResultLayerOpts) {
        var styleFunc = function(feature, style) {
            var geomType = feature.getGeometry().getType();
            var fillColor;
            if (feature.get('label') === 0) {
                fillColor = Color.GREEN.toOlColor();
            } else {
                fillColor = Color.BLUE.toOlColor();
            }
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: fillColor
                        })
                        // stroke: new ol.style.Stroke({
                        //     color: Color.WHITE.toOlColor()
                        // })
                    })
                ];
            } else if (geomType === 'Point') {
                return [
                    new ol.style.Style({
                        image: new ol.style.Circle({
                            fill: new ol.style.Fill({
                                color: fillColor
                            }),
                            radius: 2
                        })
                    })
                ];
            } else {
                throw new Error('Unknown geometry type for feature');
            }
        };
        var url = '/api/labelresults/' + opt.labelResultId + '?x={x}&y={y}&z={z}&t=' + opt.t + '&zlevel=' + opt.zlevel;

        super(name, {
            style: styleFunc,
            url: url,
            visible: opt.visible,
            size: opt.size
        });
    }
}
