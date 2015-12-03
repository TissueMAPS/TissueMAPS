type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

interface PolygonVisualOpts {
    fillColor?: Color;
    strokeColor?: Color;
}

class PolygonVisual extends Visual implements StrokeVisual, FillVisual {

    constructor(outline: PolygonCoordinates, opts?: PolygonVisualOpts) {
        var outl: PolygonCoordinatesOL = [outline];
        var geom = new ol.geom.Polygon(outl);
        var feat = new ol.Feature({
            geometry: geom
        });

        var fillColor, strokeColor;
        if (opts && opts.fillColor) {
            fillColor = opts.fillColor.toOlColor();
        } else {
            fillColor = Color.RED.toOlColor();
        }
        if (opts && opts.strokeColor) {
            strokeColor = opts.strokeColor.toOlColor();
        } else {
            strokeColor = Color.WHITE.toOlColor();
        }

        var style = new ol.style.Style({
            fill: new ol.style.Fill({
                color: fillColor
            }),
            stroke: new ol.style.Stroke({
                color: strokeColor
            })
        });

        feat.setStyle(style);
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
