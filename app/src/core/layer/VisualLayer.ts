/**
 * A short descriptor of the type content that is visualized with this
 * VisualLayer. The UI might choose to differentiate between layers of
 * different content types.
 * On Viewport all VisualLayers are stored within the same container.
 */
enum ContentType {mapObject, result, marker, default};

/**
 * Convert a string to a ContentType. This function is mainly to circumvent
 * having to pass integers in angular templates.
 */
function stringToContentType(t: string): ContentType {
    switch (t) {
        case 'mapObject': return ContentType.mapObject;
        case 'result': return ContentType.result;
        case 'marker': return ContentType.marker;
        case 'default': return ContentType.default;
        default: throw new Error('Unknown content type: ' + t);
    }
}

/**
 * Optional arguments for the VisualLayer constructor.
 */
interface VisualLayerOpts {
    visuals?: Visual[];
    visible?: boolean;
    contentType?: ContentType;
}

/**
 * Layer class for Visuals, i.e. visualizable objects.
 * This is a wrapper around an openlayers vector layer.
 */
class VisualLayer extends BaseLayer<ol.layer.VectorTile> {

    contentType: ContentType;

    private _visuals: Visual[] = [];

    constructor(name: string, projection: any, opt: VisualLayerOpts = {}) {
        super(name);

        // var vectorSource = new ol.source.Vector({
        //     features: []
        // });
        // var extent = [0, 0, 15860, 9140];
        // var extent = [0, 0, 15860, 9140];
        var extent = [0, -9140, 15860, 0];

        var vectorSource = new ol.source.VectorTile({
            // features: []
            url: 'api/experiments/adsf/mapobjects/cells?x={x}&y={y}&z={z}',
            // format: new ol.format.MVT(),
            format: new ol.format.GeoJSON({
                // NOTE: The projection has to equal the projection set on the 
                // view of the map!
                defaultDataProjection: new ol.proj.Projection({
                    code: 'tm',
                    units: 'pixels',
                    extent: extent
                })
            }),
            tileGrid: ol.tilegrid.createXYZ({
                extent: extent,
                maxZoom: 6,
                origin: [0, 0]
            })
            // tileGrid: new ol.tilegrid.TileGrid({
            //     extent: extent,
            //     // maxZoom: 7,
            //     origin: [0, 0]
            // })
        });

        this._olLayer = new ol.layer.VectorTile({
            // FIXME
            source: vectorSource,
            // style: styleFunction,
            // visible: opt.visible === undefined ? true : false
            visible: true,
            style: function(feature, style) {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: Color.RED.toOlColor()
                        }),
                        stroke: new ol.style.Stroke({
                            color: Color.WHITE.toOlColor()
                        })
                    })
                ];
            }
        });

        if (opt.visuals !== undefined) {
            this.addVisuals(opt.visuals);
        }

        this.contentType = opt.contentType !== undefined ? opt.contentType : ContentType.default;
    }

    get visuals() {
        return this._visuals;
    }

    addVisual(v: Visual) {
        // if (v !== undefined && v !== null) {
        //     this._visuals.push(v);
        //     var src = this._olLayer.getSource();
        //     var feat = v.olFeature
        //     console.log(feat);
        //     src.addFeature(feat);
        // } else {
        //     console.log('Warning: trying to add undefined or null Visual.');
        // }
    }

    addVisuals(vs: Visual[]) {
        // var visuals = [];
        // vs.forEach((v) => {
        //     if (v !== undefined && v !== null) {
        //         visuals.push(v);
        //     } else {
        //         console.log('Warning: trying to add undefined or null Visual.');
        //     }
        // });
        // visuals.forEach((v) => {
        //     this._visuals.push(v);
        // });
        // var features = _(visuals).map((v) => {
        //     var feat = v.olFeature;
        //     return feat;
        // });
        // this._olLayer.getSource().addFeatures(features);
    }

    removeVisual(v: Visual) {
        var src = this._olLayer.getSource();
        src.removeFeature(v.olFeature);
    }
}
