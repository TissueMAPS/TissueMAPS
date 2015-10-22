class SelectionLayer extends BaseLayer<ol.layer.Vector> {

    color: Color;
    cellMarkers = {};

    constructor(name: string,
                color: Color) {
        super(name);

        this.color = color;

        // TODO: Maybe the size of the marker icon should be
        // changed according to the current resolution
        var styleFunc = (feature: ol.Feature, resolution: number) => {
            var size = 42; // Compute via resolution
            // Avoid whitespaces in image name
            var colorRgbString = color.toRGBString().replace(/\s/g, '');
            console.log('asdf');
            var imageSrc =
                'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
            var style = new ol.style.Style({
                image: new ol.style.Icon({
                    // the bottom of the marker should point to the cell's
                    // center
                    anchor: [0.5, 0.9],
                    src: imageSrc
                })
            });
            return [style];
        };

        this.olLayer = new ol.layer.Vector({
            source: new ol.source.Vector(),
            style: styleFunc
        });
    }

    addCellMarker(cellId: CellId, position: MapPosition) {
        if (!this.cellMarkers.hasOwnProperty(cellId)) {
            var feat = new ol.Feature({
                geometry: new ol.geom.Point([position.x, position.y])
            });
            var src = <ol.source.Vector> this.olLayer.getSource();
            src.addFeature(feat);
            this.cellMarkers[cellId] = feat;
        }
    }

    removeCellMarker(cellId: CellId) {
        var feat = this.cellMarkers[cellId];
        if (feat) {
            var src = <ol.source.Vector> this.olLayer.getSource();
            src.removeFeature(feat);
            delete this.cellMarkers[cellId];
        }
    }

}
