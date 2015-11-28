type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

class PolygonVisual extends Visual {

    constructor(position: MapPosition, outline: PolygonCoordinates) {
        var coord = [position.x, position.y];
        var feat = new ol.Feature({
            labelPoint: new ol.geom.Point(coord)
        });
        var outl: PolygonCoordinatesOL = [outline];
        feat.setGeometry(new ol.geom.Polygon(outl));
        if (this.fillColor !== undefined) {
            var style = new ol.style.Style({
                fill: new ol.style.Fill({
                    color: this.fillColor.toOlColor()
                })
            });
            feat.setStyle(style);
        }
        super(feat);
    }
}
