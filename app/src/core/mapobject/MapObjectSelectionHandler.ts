type MapObjectSelectionByType = { [objectType: string]: MapObjectSelection[]; };

interface SerializedSelectionHandler extends Serialized<MapObjectSelectionHandler> {
    _activeSelectionId: MapObjectSelectionId;
    selections: SerializedMapObjectSelection[];
}

class MapObjectSelectionHandler implements Serializable<MapObjectSelectionHandler> {

    viewport: Viewport;

    /**
     * A hash where the selections are stored by their type.
     * When an object of class MapObjectSelectionHandler is created, the
     * active selection type will be null. For this reason there has to be an empty
     * array for this 'null' type, since otherwise this._selectionsByType[this._activeMapObjectType]
     * would be undefined, which would in turn lead to problems with angulars data binding.
     */
    private _selectionsByType: MapObjectSelectionByType = {
        null: []
    };

    private _markerSelectionModeActive: boolean = false;
    private _activeMapObjectType: MapObjectType = null;
    private _activeSelection: MapObjectSelection = null;
    private _outlineLayers: {[objectType: string]: VisualLayer;} = {};

    constructor(viewport: Viewport) {

        this.viewport = viewport;

        // Register click listeners on the map.
        this.viewport.map.then((map) => {
            map.on('singleclick', (evt) => {
                map.forEachFeatureAtPixel(evt.pixel, (feat, layer) => {
                    console.log(evt);
                    var mapObject = feat.get('mapObject');
                    var clickPos = {x: evt.coordinate[0], y: evt.coordinate[1]};
                    this.clickOnMapObject(mapObject, clickPos);
                });
            });
        });
    }

    get activeMapObjectType() {
        return this._activeMapObjectType;
    }

    set activeMapObjectType(t: MapObjectType) {
        if (!this._isValidType(t)) {
            return;
        }
        // Hide all other selections on the map
        this.supportedMapObjectTypes.forEach((t2) => {
            if (t2 !== t) {
                var sels = this.getSelectionsForType(t2);
                sels.forEach((s) => {
                    s.selectionLayer.visible = false;
                });
            }
        });
        // Show only the selections for the just activated type 
        this.getSelectionsForType(t).forEach((s) => {
            s.selectionLayer.visible = true;
        });
        this._activeMapObjectType = t;

        if (this._outlineLayers[t] !== undefined) {
            this._outlineLayers[t].visible = true;
            for (var t2 in this._outlineLayers) {
                if (t2 !== t) {
                    this._outlineLayers[t2].visible = false;
                }
            }
        }
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

    get supportedMapObjectTypes(): MapObjectType[] {
        return _.chain(this._selectionsByType).keys().difference(['null']).value();
    }

    get selectionsForActiveType(): MapObjectSelection[] {
        return this._selectionsByType[this.activeMapObjectType];
    }

    getSelectionsForType(type: string): MapObjectSelection[] {
        if (!this._isValidType(type)) {
            return [];
        }
        return this._selectionsByType[type];
    }

    addMapObjectType(t: MapObjectType) {
        this._selectionsByType[t] = [];
        if (this.activeMapObjectType === null) {
            this.activeMapObjectType = t;
        }
        // Get all objects for this type and add an outline layer to the viewport.
        // TODO: Get types
        // this.mapObjectRegistry.getMapObjectsForType(t)
        // .then((objs) => {
        //     var visuals = _(objs).map((o) => {
        //         return o.getVisual({
        //             fillColor: Color.WHITE.withAlpha(0.02),
        //             strokeColor: Color.WHITE
        //         });
        //     });

        //     var visualLayer = new VisualLayer(t, 15860, 9140, {
        //         visuals: visuals,
        //         visible: false,
        //         contentType: ContentType.mapObject
        //     });
        //     this._outlineLayers[t] = visualLayer;
        //     return this.viewport.addVisualLayer(visualLayer)
        // });
    }

    addSelection(sel: MapObjectSelection) {
        if (!this._isValidType(sel.mapObjectType)) {
            return;
        }
        this.getSelectionsForType(sel.mapObjectType).push(sel);
    }

    clickOnMapObject(mapObject: MapObject, clickPos: MapPosition) {
        console.log('Clicked on: ', mapObject);
        if (!this._isValidType(mapObject.type)) {
            return;
        }
        if (this._markerSelectionModeActive) {
            var sel = this.activeSelection;
            if (sel) {
                sel.addRemoveMapObject(mapObject, clickPos);
            } else {
                console.log('No active selection found');
            }
        }
        // TODO: Issue some kind of "clicked on mapobject X type of event and callback
        // registered listeners"
    }

    getSelection(type: string, selectionId: MapObjectSelectionId): MapObjectSelection {
        if (!this._isValidType(type)) {
            return undefined;
        }
        var selections = this.getSelectionsForType(type);
        return _(selections).find((s) => {
            return s.id === selectionId;
        });
    }

    addNewSelection(type: string) {
        if (!this._isValidType(type)) {
            return undefined;
        }
        var id = this.getSelectionsForType(type).length;
        var color = this._getNextColor(type);
        var newSel = new MapObjectSelection(id, type, color);
        newSel.visualizeOnViewport(this.viewport);
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
        var sels = this.getSelectionsForType(type);
        var nColors = MapObjectSelection.availableColors.length;
        var possibleIds = _.range(nColors);
        var usedIds = _(sels).map(function(s) { return s.id % nColors; });
        var availableIds = _.difference(possibleIds, usedIds);
        // throw new Error(JSON.stringify(availableIds));
        if (availableIds.length != 0) {
            var id = availableIds[0];
            return MapObjectSelection.availableColors[id];
        } else {
            return MapObjectSelection.availableColors[
                sels.length % MapObjectSelection.availableColors.length
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

    private _isValidType(t: MapObjectType) {
        if (t === undefined || this._selectionsByType[t] === undefined) {
            console.log('Not a valid type: ', t);
            return false;
        } else {
            return true;
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

