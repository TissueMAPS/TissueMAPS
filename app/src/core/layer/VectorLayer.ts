/**
 * Optional arguments for the VectorLayer constructor.
 */
interface VectorLayerArgs {
    visuals?: Visual[];
    visible?: boolean;
}

/**
 * Layer class for Visuals, i.e. visualizable objects.
 * This is a wrapper around an openlayers vector layer.
 */
class VectorLayer extends BaseLayer<ol.layer.Vector> {

    private _visuals: Visual[] = [];

    constructor(args: VectorLayerArgs = {}) {
        super();

        var vectorSource = new ol.source.Vector({
            features: []
        });

        this._olLayer = new ol.layer.Vector({
            source: vectorSource,
            visible: args.visible === undefined ? true : false
        });

        if (args.visuals !== undefined) {
            this.addVisuals(args.visuals);
        }
    }

    get visuals() {
        return this._visuals;
    }

    addVisual(v: Visual) {
        if (v !== undefined && v !== null) {
            this._visuals.push(v);
            var src = this._olLayer.getSource();
            var feat = v.olFeature
            src.addFeature(feat);
        } else {
            console.log('Warning: trying to add undefined or null Visual.');
        }
    }

    addVisuals(vs: Visual[]) {
        var visuals = [];
        vs.forEach((v) => {
            if (v !== undefined && v !== null) {
                visuals.push(v);
            } else {
                console.log('Warning: trying to add undefined or null Visual.');
            }
        });
        visuals.forEach((v) => {
            this._visuals.push(v);
        });
        var features = _(visuals).map((v) => {
            var feat = v.olFeature;
            return feat;
        });
        this._olLayer.getSource().addFeatures(features);
    }

    removeVisual(v: Visual) {
        var src = this._olLayer.getSource();
        src.removeFeature(v.olFeature);
    }
}
