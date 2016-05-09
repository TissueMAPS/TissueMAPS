interface LabelColorMapper {
    (label: any): Color;
}

interface LabelLayerArgs {
    id: string;
    attributes: any;
    t: number;
    zlevel: number;
    visible?: boolean;
}

abstract class LabelLayer extends VectorTileLayer {
    
    id: string;
    attributes: any;

    abstract getLabelColorMapper(): LabelColorMapper;
    abstract getLegend(): Legend;

    constructor(args: LabelLayerArgs) {
        var styleFunc = (feature, style) => {
            var colorMapper = this.getLabelColorMapper();
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
        var url = '/api/labellayers/' + args.id + '/tiles?x={x}&y={y}&z={z}&t=' + args.t + '&zlevel=' + args.zlevel;

        var app = $injector.get<Application>('application');
        var size = app.activeViewer.viewport.mapSize;

        super({
            style: styleFunc,
            url: url,
            visible: args.visible,
            size: size
        });

        this.id = args.id;
        this.attributes = args.attributes;
    }
}
