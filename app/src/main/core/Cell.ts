type CellId = string;

interface ICell {
    id: CellId;
    centroid: IMapPosition;
}

class Cell implements ICell {
    constructor(public id: CellId, public centroid: IMapPosition) {
    }
}

angular.module('tmaps.core')
.factory('Cell', () => {
    return Cell;
});
