type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;

interface PolygonVisualOpts extends ColorizableOpts {
}

class PolygonVisual extends ColorizableVisual {

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

    strokeColor: Color;
}
