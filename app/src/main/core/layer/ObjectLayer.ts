interface ObjectLayerArgs {
    objects?: MapObject[];
}

class ObjectLayer extends Layer {
    olLayer: ol.layer.Vector;
    styles: any;

    constructor(private ol, name: string, opt: ObjectLayerArgs = {}) {
        super(name)

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

        if (opt.objects !== undefined) {
            var features = _(opt.objects).map((o) => { return o.getOLFeature(); });
            this.olLayer.getSource().addFeatures(features);
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
                    color: 'rgba(0, 0, 255, 1)',
                    lineDash: [4],
                    width: 3
                }),
                fill: new this.ol.style.Fill({
                    color: 'rgba(0, 0, 255, 0.5)'
                })
            })]
        };
    }

    addObject(obj: MapObject) {
        this.olLayer.getSource().addFeature(obj.getOLFeature());
    }

    addObjects(objs: MapObject[]) {
        _(objs).each((obj) => {
            this.addObject(obj);
        });
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
    create(name: string) {
        return new ObjectLayer(this.ol, name);
    }
}

angular.module('tmaps.core.layer').service('ObjectLayerFactory', ObjectLayerFactory);
