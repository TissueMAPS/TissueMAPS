interface VectorTileLayerOpts {
    url: string;
    size: Size;
    style?: ol.style.Style | ol.FeatureStyleFunction;
    visible?: boolean;
}

class VectorTileLayer extends BaseLayer<ol.layer.VectorTile> {

    private _fillColor: Color = Color.WHITE.withAlpha(0);
    private _strokeColor: Color = Color.WHITE;

    set fillColor(c: Color) {
        this._fillColor = c;
        this._olLayer.changed();
    }

    set strokeColor(c: Color) {
        this._strokeColor = c;
        this._olLayer.changed();
    }

    get fillColor() {
        return this._fillColor;
    }

    get strokeColor() {
        return this._strokeColor;
    }

    private _createDefaultStyleFunc() {
        return (feature, style) => {
            var geomType = feature.getGeometry().getType();
            if (geomType === 'Polygon') {
                return [
                    new ol.style.Style({
                        fill: new ol.style.Fill({
                            color: this.fillColor.toOlColor()
                        }),
                        stroke: new ol.style.Stroke({
                            color: this.strokeColor.toOlColor(),
                        })
                    })
                ];
            } else if (geomType === 'Point') {
                return [
                    new ol.style.Style({
                        image: new ol.style.Circle({
                            fill: new ol.style.Fill({
                                color: this.strokeColor.toOlColor()
                            }),
                                  // ,
                            // stroke: new ol.style.Stroke({
                            //     color: this.strokeColor.toOlColor()
                            // }),
                            radius: 2
                        })
                    })
                ];
            } else {
                throw new Error('Unknown geometry type for feature');
            }
        };
    }

    constructor(opt?: VectorTileLayerOpts) {
        super();

        var opt = opt === undefined ? <VectorTileLayerOpts> {} : opt;
        
        // Same extent as zoomify
        var extent = [0, -opt.size.height, opt.size.width, 0];

        var vectorSource = new ol.source.VectorTile({
            url: opt.url,
            format: new ol.format.GeoJSON({
                defaultDataProjection: new ol.proj.Projection({
                    code: 'tm',
                    units: 'pixels',
                    extent: extent
                })
            }),
            tileGrid: ol.tilegrid.createXYZ({
                extent: extent,
                maxZoom: 22,
                origin: [0, 0]
            })
        });

        this._olLayer = new ol.layer.VectorTile({
            source: vectorSource,
            visible: opt.visible,
            style: opt.style !== undefined ? opt.style : this._createDefaultStyleFunc()
        });
    }
}
