interface ObjectLayerArgs {
    objects?: MapObject[];
    strokeColor?: string;
    fillColor?: string;
}

class ObjectLayer extends Layer {
    olLayer: ol.layer.Vector;
    styles: any;

    defaultStrokeColor = 'rgba(0, 0, 255, 1)';
    defaultFillColor = 'rgba(0, 0, 255, 0.5)';

    constructor(private ol, name: string, opt: ObjectLayerArgs = {}) {
        super(name);

        var vectorSource = new ol.source.Vector({
            features: []
        });

        var styleFunction = (feature, resolution) => {
            return this.styles[feature.getGeometry().getType()];
        }

        this.olLayer = new ol.layer.Vector({
            source: vectorSource,
            style: styleFunction
        });

        console.log(opt);
        if (opt.objects !== undefined) {
            this.addObjects(opt.objects);
        }

        this.styles = {
            'Point': [new this.ol.style.Style({
                image: new this.ol.style.Circle({
                    radius: 5,
                    fill: null,
                    stroke: new this.ol.style.Stroke({color: 'red', width: 1})
                })
            })],
            'Polygon': [new this.ol.style.Style({
                stroke: new this.ol.style.Stroke({
                    color: opt.strokeColor || this.defaultStrokeColor,
                    lineDash: [4],
                    width: 2
                }),
                fill: new this.ol.style.Fill({
                    color: opt.fillColor || this.defaultFillColor
                })
            })]
        };

        console.log(this.styles);
    }

    addObject(obj: MapObject) {
        this.olLayer.getSource().addFeature(obj.getOLFeature());
    }

    addObjects(objs: MapObject[]) {
        console.log('bla');
        var features = _(objs).map((o) => { return o.getOLFeature(); });
        this.olLayer.getSource().addFeatures(features);
    }

    addFeaturesFromGeoJSON(obj: JSON) {
        var feats: ol.Feature[] = (new ol.format.GeoJSON()).readFeatures(obj);
        var source = this.olLayer.getSource();
        source.addFeatures(feats);
    }
}

class ObjectLayerFactory {
    static $inject = ['openlayers'];
    constructor(private ol) {}
    create(name: string, opt: ObjectLayerArgs = {}) {
        return new ObjectLayer(this.ol, name, opt);
    }
}

angular.module('tmaps.core.layer').service('ObjectLayerFactory', ObjectLayerFactory);
