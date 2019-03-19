// Copyright (C) 2016-2018 University of Zurich.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
type MapObjectSelectionId = number;

interface SelectionEntry {
    markerPosition: MapPosition;
    mapObject: MapObject;
    markerVisual: MarkerImageVisual;
}

class MapObjectSelection implements Serializable<MapObjectSelection> {

    static availableColors = [
        new Color(228,26,28),
        new Color(55,126,184),
        new Color(77,175,74),
        new Color(152,78,163),
        new Color(255,127,0),
        new Color(255,255,51),
        new Color(166,86,40),
        new Color(247,129,191),
        new Color(153,153,153)
    ];

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

        this._layer = new SelectionLayer(this.name, {
            color: this.color
        });

        this._$rootScope = $injector.get<ng.IRootScopeService>('$rootScope');
    }

    get selectionLayer() {
        return this._layer;
    }

    visualizeOnViewport(vp: Viewport) {
        vp.addLayer(this._layer);
    }

    get mapObjects() {
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
            var entry = this._entries[mapObject.id];
            this._layer.removeVisual(entry.markerVisual);
            delete this._entries[mapObject.id];
            this._$rootScope.$emit('change:MapObjectSelection', this);
        };
    }

    addMapObject(mapObject: MapObject, markerPos: MapPosition) {
        if (!this.isMapObjectSelected(mapObject)) {
            var visual = new MarkerImageVisual(markerPos, this.color);
            this._entries[mapObject.id] = {
                mapObject: mapObject,
                markerPosition: markerPos,
                markerVisual: visual
            };
            this._$rootScope.$emit('change:MapObjectSelection', this);
            this._layer.addVisual(visual);
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
        this._$rootScope.$emit('change:MapObjectSelection', this);
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
