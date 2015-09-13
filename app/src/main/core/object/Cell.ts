type CellId = string;

class Cell implements MapObject {
    constructor(public id: CellId, public centroid: MapPosition) {
    }

    getOLFeature() {
        var coord = [this.centroid.x, this.centroid.y];
        return new ol.Feature({
            geometry: new ol.geom.Point(coord),
            labelPoint: new ol.geom.Point(coord),
            name: this.id
        });
    }
}

angular.module('tmaps.core')
.factory('Cell', () => {
    return Cell;
});
