class PointVisual extends Visual {
    constructor(position: MapPosition) {
        var coord = [position.x, position.y];
        var feat = new ol.Feature({
            labelPoint: new ol.geom.Point(coord)
        });
        var style = new ol.style.Style({
            fill: new ol.style.Fill({
                color: Color.RED.toOlColor()
            })
        });
        feat.setStyle(style);
        super(feat);
    }
}
