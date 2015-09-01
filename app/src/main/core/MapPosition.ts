interface IMapPosition {
    x: number;
    y: number;
}

class MapPosition implements IMapPosition {
    constructor(public x: number, public y: number) {}
}

angular.module('tmaps.core')
.factory('MapPosition', () => {
    return MapPosition;
});
