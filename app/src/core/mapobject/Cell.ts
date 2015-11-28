class Cell implements MapObject {

    type = 'cell';

    constructor(public id: string,
                public position: MapPosition,
                public outline: PolygonCoordinates) {}

    getVisual(): Visual {
        return new PolygonVisual(this.position, this.outline);
    }
}

angular.module('tmaps.core')
.factory('Cell', () => {
    return Cell;
});
