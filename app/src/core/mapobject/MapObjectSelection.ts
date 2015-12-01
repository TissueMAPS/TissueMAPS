type MapObjectSelectionId = number;
interface SelectionEntry {
    markerPosition: MapPosition;
    mapObject: MapObject;
}

class MapObjectSelection implements Serializable<MapObjectSelection> {

    id: MapObjectSelectionId;
    name: string;
    mapObjectType: string;

    color: Color;

    private _entries: { [objectId: number]: SelectionEntry; } = {};
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

    addToMap(map: ol.Map) {
        this._layer.addToMap(map);
    }

    getMapObjects() {
        var objects = [];
        for (var mapObjectId in this._entries) {
            var entry = this._entries[mapObjectId];
            objects.push(entry.mapObject);
        }
        return objects;
    }

    removeFromMap(map: ol.Map) {
        // Somehow the markers won't get removed when removing the layer
        // and clear needs to be called beforehand.
        this.clear();
        this._layer.removeFromMap(map);
    }

    isMapObjectSelected(mapObject: MapObject) {
        return this._entries.hasOwnProperty(mapObject.id.toString());
    }

    removeMapObject(mapObject: MapObject) {
        if (this.isMapObjectSelected(mapObject)) {
            delete this._entries[mapObject.id];
            this._layer.removeMapObjectMarker(mapObject.id);
            this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
        };
    }

    addMapObject(mapObject: MapObject, markerPos?: MapPosition) {
        if (!this.isMapObjectSelected(mapObject)) {
            this._entries[mapObject.id] = {
                markerPosition: markerPos,
                mapObject: mapObject
            };
            this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
            if (markerPos !== undefined) {
                this._layer.addMapObjectMarker(mapObject.id, markerPos);
            }
        }
    }

    addRemoveMapObject(mapObject: MapObject, markerPos?: MapPosition) {
        if (this.isMapObjectSelected(mapObject)) {
            this.removeMapObject(mapObject);
        } else {
            this.addMapObject(mapObject, markerPos)
        }
    }

    /**
     * Remove all _entries from this selection, but don't delete it.
     */
    clear() {
        // TODO: Consider doing this via some batch mechanism if it proves to be slow
        for (var k in this._entries) {
            var o = this._entries[k].mapObject;
            this.removeMapObject(o);
        }
        this._$rootScope.$broadcast('mapObjectSelectionChanged', this);
    }

    serialize() {
        return this.color.serialize().then((serColor) => {
            var ser = {
                id: this.id,
                entries: this._entries,
                color: serColor
            };
            return ser;
        });
    }

}

interface SerializedMapObjectSelection extends Serialized<MapObjectSelection> {
    id: MapObjectSelectionId;
    entries: { [mapObjectId: number]: SelectionEntry; };
    color: SerializedColor;
}
