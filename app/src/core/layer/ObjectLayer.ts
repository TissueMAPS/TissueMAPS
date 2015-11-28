interface VisualLayerArgs {
    visuals?: Visual[];
    strokeColor?: Color;
    fillColor?: Color;
    visible?: boolean;
}

class VisualLayer extends BaseLayer<ol.layer.Vector> {
    styles: any;

    private strokeColor: Color;
    private fillColor: Color;

    private defaultStrokeColor = new Color(255, 0, 0);
    private defaultFillColor = new Color(255, 0, 0, 0.1);

    private _visuals: Visual[] = [];

    constructor(name: string, opt: VisualLayerArgs = {}) {
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

        if (opt.visuals !== undefined) {
            this.addVisuals(opt.visuals);
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

    getVisuals() {
        return this._visuals;
    }

    addVisual(v: Visual) {
        if (v !== undefined && v !== null) {
            this._visuals.push(v);
            var src = this.olLayer.getSource();
            var feat = v.olFeature
            src.addFeature(feat);
        } else {
            console.log('Warning: trying to add undefined or null Visual.');
        }
    }

    addVisuals(vs: Visual[]) {
        var visuals = _(vs).filter((v) => {
            return v !== undefined && v !==  null;
        });
        visuals.forEach((v) => {
            this._visuals.push(v);
        });
        var features = _(visuals).map((v) => {
            var feat = v.olFeature;
            return feat;
        });
        this.olLayer.getSource().addFeatures(features);
    }
}
