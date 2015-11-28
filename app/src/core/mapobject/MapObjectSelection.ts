type MapObjectSelectionId = number;

class MapObjectSelection implements Serializable<MapObjectSelection> {

    id: MapObjectSelectionId;
    name: string;
    mapObjectType: string;

    color: Color;

    mapObjects: { [objectId: string]: MapPosition; } = {};

    private _layer: SelectionLayer;
    private _$rootScope: ng.IRootScopeService;

    constructor(id: MapObjectSelectionId,
                mapObjectType: string,
                color: Color) {

        this.id = id;
        this.mapObjectType = mapObjectType;
        this.color = color;
        this.name = 'Selection #' + id;

        this._layer = new SelectionLayer(this.name, this.color);

        this._$rootScope = $injector.get<ng.IRootScopeService>('$rootScope');
    }

    // TODO: Is this used anywhere?
    addToMap(map: ol.Map) {
        this._layer.addToMap(map);
    }

    getMapObjects() {
        var mapObjectIds =
            _.chain(this.mapObjects)
             .keys()
             .map(function(k) { return parseInt(k); })
             .value();
        return mapObjectIds;
    }

    removeFromMap(map: ol.Map) {
        // Somehow the markers won't get removed when removing the layer
        // and clear needs to be called beforehand.
        this.clear();
        this._layer.removeFromMap(map);
    }

    removeMapObject(mapObjectId: MapObjectId) {
        if (this.mapObjects.hasOwnProperty(mapObjectId)) {
            delete this.mapObjects[mapObjectId];
            this._layer.removeMapObjectMarker(mapObjectId);
        };
        this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
    }

    /**
     * Remove all mapObjects from this selection, but don't delete it.
     */
    clear() {
        // TODO: Consider doing this via some batch mechanism if it proves to be slow
        _.keys(this.mapObjects).forEach((mapObjectId: MapObjectId) => {
            this.removeMapObject(mapObjectId);
        });
        this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
    }

    addMapObjectAt(markerPos: MapPosition, mapObjectId: MapObjectId) {
        if (this.mapObjects.hasOwnProperty(mapObjectId)) {
            this.removeMapObject(mapObjectId);
        } else {
            this.mapObjects[mapObjectId] = markerPos;
            this._layer.addMapObjectMarker(mapObjectId, markerPos);
        }
        this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
    }

    isMapObjectSelected(mapObject: MapObject) {
        return this.mapObjects[mapObject.id] !== undefined;
    }

    serialize() {
        return this.color.serialize().then((serColor) => {
            var ser = {
                id: this.id,
                mapObjects: this.mapObjects,
                color: serColor
            };
            return ser;
        });
    }

}


interface SerializedMapObjectSelection extends Serialized<MapObjectSelection> {
    id: MapObjectSelectionId;
    mapObjects: { [mapObjectId: string]: MapPosition; };
    color: SerializedColor;
}
