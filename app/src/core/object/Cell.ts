type PolygonCoordinates = Array<ol.Coordinate>;
type PolygonCoordinatesOL = Array<Array<ol.Coordinate>>;
type CellId = string;

class Cell implements MapObject {

    constructor(public id: CellId,
                public position: MapPosition,
                public outline?: PolygonCoordinates,
                public fillColor?: Color) {
    }

    withFillColor(color: Color) {
        return new Cell(this.id, this.position, this.outline, color);
    }

    getOLFeature(): ol.Feature {
        var coord = [this.position.x, this.position.y];
        var feat = new ol.Feature({
            labelPoint: new ol.geom.Point(coord),
            name: this.id
        });
        if (this.outline === undefined) {
            feat.setGeometry(new ol.geom.Point(coord));
        } else {
            var outl: PolygonCoordinatesOL = [this.outline];
            feat.setGeometry(new ol.geom.Polygon(outl));
        }
        if (this.fillColor !== undefined) {
            var style = new ol.style.Style({
                fill: new ol.style.Fill({
                    color: this.fillColor.toOlColor()
                })
            });
            feat.setStyle(style);
        }
        return feat;
    }
}

angular.module('tmaps.core')
.factory('Cell', () => {
    return Cell;
});
