/**
 * A function that maps a mapobject label to some color.
 */
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

    private _colorMapper: LabelColorMapper;

    /**
     * Each specific implmentation of a LabelLayer should provide a function
     * that maps labels that were given to mapobjects by some tool to a
     * specific color.
     */
    abstract getLabelColorMapper(): LabelColorMapper;

    /**
     * Each specific implementation of a LabelLayer can provide a legend that
     * is displayed beside the layer and that explains how the colors are to be
     * interpreted.
     */
    abstract getLegend(): Legend;

    /**
     * It's important that the getLabelColorMapper() method is only called
     * once since constructing the colorMapper might be an expensive operation.
     */
    get colorMapper() {
        if (this._colorMapper === undefined) {
            this._colorMapper = this.getLabelColorMapper();
        }
        return this._colorMapper;
    }

    /**
     * Construct an object of type LabelLayer.
     * @class LabelLayerArgs
     * @classdesc A labellayer is a type of layer that will request its vector
     * features from the server. This layer type is similar to a SegmentationLayer.
     * However, in contrast to a standard SegmentationLayer, the features that
     * are sent by the server contain a 'label' attribute that is set to the
     * label that the original tool assigned to the respective mapobject.
     * Each polygon/point is colored according to this label.
     */
    constructor(args: LabelLayerArgs) {
        var styleFunc = (feature, style) => {
            var geomType = feature.getGeometry().getType();
            var label = feature.get('label');
            var fillColor: ol.Color;
            if (label !== undefined) {
                fillColor = this.colorMapper(label).toOlColor();
            } else {
                throw new Error('Feature has no property "label"!');
            }
            if (geomType === 'Polygon' || geomType === 'Point') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: fillColor
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
