type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

class PolygonVisual extends Visual implements StrokeVisual, FillVisual {

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

    get fillColor() {
        // Color.fromOlColor(this.olFeature.getStyle.fill);
        return Color.RED;
    }

    set fillColor(c: Color) {
        // Color.fromOlColor(this.olFeature.getStyle.fill);
        // return Color.RED;
    }

    get strokeColor() {
        // Color.fromOlColor(this.olFeature.getStyle.stroke);
        return Color.RED;
    }

    set strokeColor(c: Color) {
        // Color.fromOlColor(this.olFeature.getStyle.stroke);
        // return Color.RED;
    }
}
