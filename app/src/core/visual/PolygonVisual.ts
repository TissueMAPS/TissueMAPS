type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

class PolygonVisual extends Visual implements StrokeVisual, FillVisual {

    constructor(outline: PolygonCoordinates) {
        var outl: PolygonCoordinatesOL = [outline];
        var geom = new ol.geom.Polygon(outl);
        var feat = new ol.Feature({
            geometry: geom
        });
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
