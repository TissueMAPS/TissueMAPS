interface LabelResultLayerArgs {
    labelResultId: number;
    t: number;
    zlevel: number;
    size: Size;
    labelColorMapper: LabelColorMapper;
    visible?: boolean;
}


class LabelResultLayer extends VectorTileLayer {
    constructor(args: LabelResultLayerArgs) {
        var colorMapper = args.labelColorMapper;
        var styleFunc = function(feature, style) {
            var geomType = feature.getGeometry().getType();
            var label = feature.get('label');
            var fillColor: ol.Color;
            if (label !== undefined) {
                fillColor = colorMapper(label).toOlColor();
            } else {
                throw new Error('Feature has no property "label"!');
            }
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: fillColor
                        })
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
        var url = '/api/labelresults/' + args.labelResultId + '?x={x}&y={y}&z={z}&t=' + args.t + '&zlevel=' + args.zlevel;

        super({
            style: styleFunc,
            url: url,
            visible: args.visible,
            size: args.size
        });
    }
}
