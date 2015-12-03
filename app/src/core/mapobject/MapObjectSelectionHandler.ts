type MapObjectSelectionByType = { [objectType: string]: MapObjectSelection[]; };

interface SerializedSelectionHandler extends Serialized<MapObjectSelectionHandler> {
    _activeSelectionId: MapObjectSelectionId;
    selections: SerializedMapObjectSelection[];
}

class MapObjectSelectionHandler implements Serializable<MapObjectSelectionHandler> {

    viewport: Viewport;

    availableColors: Color[];

    private _selectionsByType: MapObjectSelectionByType = {};
    private _markerSelectionModeActive: boolean = false;
    private _activeMapObjectType: MapObjectType = null;
    private _activeSelection: MapObjectSelection = null;

    constructor(viewport: Viewport) {

        this.viewport = viewport;

        var colorsRGBString = [
            'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)',
            'rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)',
            'rgb(153,153,153)'
        ];
        var availableColors = _(colorsRGBString).map((rgb) => {
            return Color.fromRGBString(rgb);
        });
        this.availableColors = availableColors;
    }

    get activeMapObjectType() {
        return this._activeMapObjectType;
    }

    set activeMapObjectType(t: MapObjectType) {
        this._checkObjectType(t);
        this._activeMapObjectType = t;
    }

    /**
     * Set the active selection, i.e., the selection to which new objects
     * are added.
     *
     * By passing null as the argument, the currently active selection will be 
     * set as inactive.
     */
    set activeSelection(sel: MapObjectSelection) {
        if (sel === null) {
            this._activeSelection = null;
        } else {
            this._activeSelection = sel;
        }
    }

    /**
     * Get the selection that is currently active.
     *
     * If no selection is chosen as active, the return value will be null.
     */
    get activeSelection(): MapObjectSelection {
        return this._activeSelection;
    }

    getSelectionsForType(type: string) {
        this._checkObjectType(type);
        return this._selectionsByType[type];
    }

    addMapObjectType(t: MapObjectType) {
        this._selectionsByType[t] = [];
        if (this.activeMapObjectType === null) {
            this.activeMapObjectType = t;
        }
        // this.addNewSelection(t);
    }


    addMapObjectOutlines(cells: MapObject[]) {
        // TODO: Generalize and implement
        // var cellLayer = new MapObjectLayer('MapObjects', {
        //     objects: cells,
        //     // Upon testing 0.002 was the lowest alpha value which still caused to
        //     // hitDetection mechanism to find the cell. Lower values get probably floored to 0.
        //     fillColor: Color.RED.withAlpha(0.005),
        //     strokeColor: Color.WHITE,
        //     visible: false
        // });
        // this.viewport.addMapObjectLayer(cellLayer);
        // this.viewport.map.then((map) => {
        //     map.on('singleclick', (evt) => {
        //         map.forEachFeatureAtPixel(evt.pixel, (feat, layer) => {
        //             console.log(evt);
        //             // FIXME: Maybe we should save the whole mapobject on the feature, or
        //             // subclass Feature directly.
        //             var mapObjectId = feat.get('name');
        //             var clickPos = {x: evt.coordinate[0], y: evt.coordinate[1]};
        //             if (this._activeSelectionId !== -1) {
        //                 this.clickOnMapObject(clickPos, mapObjectId);
        //             }
        //         });
        //     });
        // });
    }

    addSelection(sel: MapObjectSelection) {
        this._checkObjectType(sel.mapObjectType);
        this.getSelectionsForType(sel.mapObjectType).push(sel);
    }

    clickOnMapObject(mapObject: MapObject, clickPos: MapPosition) {
        this._checkObjectType(mapObject.type);
        if (this._markerSelectionModeActive) {
            var sel = this.activeSelection;
            if (sel) {
                sel.addMapObject(mapObject, clickPos);
            } else {
                console.log('No active selection found');
            }
        }
    }

    // addMapObjectToSelection(markerPosition: MapPosition,
    //                         mapObject: MapObject,
    //                         selectionId: MapObjectSelectionId) {
    //     this.selections[mapObject]
    //     var selection = this.getSelectionById(selectionId);
    //     if (selection === undefined) {
    //         throw new Error('Unknown selection id: ' + selectionId);
    //     }
    //     selection.addMapObjectAt(markerPosition, mapObjectId);
    // }

    getSelection(type: string, selectionId: MapObjectSelectionId): MapObjectSelection {
        this._checkObjectType(type);
        var selections = this.getSelectionsForType(type);
        return _(selections).find((s) => {
            return s.id === selectionId;
        });
    }

    // getSelectedMapObjects(selectionId: MapObjectSelectionId) {
    //     var sel = this.getSelectionById(selectionId);
    //     return sel !== undefined ? sel.getMapObjects() : [];
    // }

    addNewSelection(type: string) {
        this._checkObjectType(type);
        var id = this.getSelectionsForType(type).length;
        var color = this._getNextColor(type);
        var newSel = new MapObjectSelection(id, type, color);
        this.viewport.map.then((map) => {
            newSel.addToMap(map);
        });
        this.addSelection(newSel);
        return newSel;
    }

    activateMarkerSelectionMode() {
        this._markerSelectionModeActive = true;
    }

    deactivateMarkerSelectionMode() {
        this._markerSelectionModeActive = false;
    }

    isMarkerSelectionModeActive() {
        return this._markerSelectionModeActive;
    }

    private _getNextColor(type: string) {
        this._checkObjectType(type);
        var sels = this.getSelectionsForType(type);
        var nColors = this.availableColors.length;
        var possibleIds = _.range(nColors);
        var usedIds = _(sels).map(function(s) { return s.id % nColors; });
        var availableIds = _.difference(possibleIds, usedIds);
        // throw new Error(JSON.stringify(availableIds));
        if (availableIds.length != 0) {
            var id = availableIds[0];
            return this.availableColors[id];
        } else {
            return this.availableColors[
                sels.length % this.availableColors.length
            ];
        }
    }

    removeSelection = function(sel: MapObjectSelection) {
        if (sel) {
            if (sel === this._activeSelection) {
                this.activeSelection = null;
            }
            this.viewport.map.then((map: ol.Map) => {
                sel.removeFromMap(map);
            });
            var selections = this.getSelectionsForType(sel.mapObjectType);
            selections.splice(selections.indexOf(sel), 1);
        } else {
            console.log('Trying to delete nonexistant selection with id ' + sel.id);
        }
    };

    private _checkObjectType(t: MapObjectType) {
        if (this._selectionsByType[t] === undefined) {
            throw new Error('Not a supported type. Did you add it already?');
        }
    }

    serialize() {
        var $q = $injector.get<ng.IQService>('$q');
        var selectionPromisesPerType = {};
        // For all the selections of each type
        for (var type in this._selectionsByType) {
            var selections = this._selectionsByType[type];
            // serialize each selection individually
            var promises = _(selections).map((sel) => { return sel.serialize(); });
            // and wrap all the individual promises inside an `all`-promise.
            selectionPromisesPerType[type] = $q.all(promises);
        }
        // When all of the promises are resolved create the serialized
        // mapObjectSelectionHandler.
        return $q.all(<any>selectionPromisesPerType).then((selections) => {
            var ser = {
                activeSelectionId: this._activeSelection === null ? -1 : this._activeSelection.id,
                selections: selections
            };
            return ser;
        });
    }
}

