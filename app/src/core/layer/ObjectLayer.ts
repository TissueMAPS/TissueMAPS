interface ObjectLayerArgs {
    objects?: MapObject[];
    strokeColor?: Color;
    fillColor?: Color;
    visible?: boolean;
}

class ObjectLayer extends Layer {
    olLayer: ol.layer.Vector;
    styles: any;

    private strokeColor: Color;
    private fillColor: Color;

    private defaultStrokeColor = new Color(255, 0, 0);
    private defaultFillColor = new Color(255, 0, 0, 0.1);

    private _objects: MapObject[] = [];

    constructor(name: string, opt: ObjectLayerArgs = {}) {
        super(name);

        var vectorSource = new ol.source.Vector({
            features: []
        });

        var styleFunction = (feature, resolution) => {
            return this.styles[feature.getGeometry().getType()];
        }

        this.olLayer = new ol.layer.Vector({
            source: vectorSource,
            style: styleFunction,
            visible: opt.visible === undefined ? true : false
        });

        if (opt.objects !== undefined) {
            this.addObjects(opt.objects);
        }

        if (opt.strokeColor === undefined) {
            this.strokeColor = this.defaultStrokeColor;
        } else if (opt.strokeColor === null) {
            this.strokeColor = new Color(0, 0, 0, 0);
        } else {
            this.strokeColor = opt.strokeColor;
        }

        if (opt.fillColor === undefined) {
            this.fillColor = this.defaultFillColor;
        } else if (opt.fillColor === null) {
            this.fillColor = new Color(0, 0, 0, 0);
        } else {
            this.fillColor = opt.fillColor;
        }

        var olStrokeColor = this.strokeColor === null ? null : this.strokeColor.toRGBAString();
        var olFillColor = this.fillColor === null ? null : this.fillColor.toRGBAString();

        this.styles = {
            'Point': [new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 5,
                    fill: null,
                    stroke: new ol.style.Stroke({color: olStrokeColor, width: 1})
                })
            })],
            'Polygon': [new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: olStrokeColor,
                    lineDash: [1],
                    width: 1
                }),
                fill: new ol.style.Fill({
                    color: olFillColor
                })
            })]
        };
    }

    getObjects() {
        return this._objects;
    }

    addObject(obj: MapObject) {
        if (obj !== undefined && obj !== null) {
            this._objects.push(obj);
            var src = this.olLayer.getSource();
            src.addFeature(obj.getOLFeature());
        } else {
            console.log('Warning: trying to add undefined or null MapObject.');
        }
    }

    addObjects(objs: MapObject[]) {
        var objects = _(objs).filter((o) => {
            return o !== undefined && o !==  null;
        });
        objects.forEach((o) => {
            this._objects.push(o);
        });
        var features = _(objects).map((o) => { return o.getOLFeature(); });
        this.olLayer.getSource().addFeatures(features);
    }
}
