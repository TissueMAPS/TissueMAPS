interface VisualTileLayerOpts {
    url: string;
    size: Size;
    style: ol.style.Style | ol.FeatureStyleFunction;
    visible?: boolean;
}

class VisualTileLayer extends BaseLayer<ol.layer.VectorTile> {

    constructor(name: string, 
                opt?: VisualTileLayerOpts) {
        super(name);

        var opt = opt === undefined ? <VisualTileLayerOpts> {} : opt;
        
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
            style: opt.style
        });
    }
}
