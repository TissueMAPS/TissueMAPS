interface VisualTileLayerOpts {
    url: string;
    imageWidth: number,
    imageHeight: number,
    style: ol.style.Style | ol.FeatureStyleFunction;
    visible?: boolean;
}

class VisualTileLayer extends BaseLayer<ol.layer.VectorTile> {

    constructor(name: string, 
                opt?: VisualTileLayerOpts) {
        super(name);

        var opt = opt === undefined ? <VisualTileLayerOpts> {} : opt;
        
        // Same extent as zoomify
        var extent = [0, -opt.imageHeight, opt.imageWidth, 0];

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
                maxZoom: 6, // TODO: set this
                origin: [0, 0]
            })
        });

        this._olLayer = new ol.layer.VectorTile({
            source: vectorSource,
            visible: true,
            style: opt.style
            // style: function(feature, style) {
            //     var geomType = feature.getGeometry().getType();
            //     if (geomType === 'Polygon') {
            //         return [
            //             new ol.style.Style({
            //                 fill: new ol.style.Fill({
            //                     color: Color.GREEN.toOlColor()
            //                 }),
            //                 stroke: new ol.style.Stroke({
            //                     color: Color.WHITE.toOlColor()
            //                 })
            //             })
            //         ];
            //     } else if (geomType === 'Point') {
            //         return [
            //             new ol.style.Style({
            //                 image: new ol.style.Circle({
            //                     fill: new ol.style.Fill({
            //                         color: [0, 255, 0, 1]
            //                     }),
            //                     radius: 2
            //                 })
            //             })
            //         ];
            //     } else {
            //         throw new Error('Unknown geometry type for feature');
            //     }
            // }
        });
    }
}
