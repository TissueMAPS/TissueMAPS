interface SerializedSelectionHandler extends Serialized<MapObjectSelectionHandler> {
    activeSelectionId: MapObjectSelectionId;
    selections: SerializedMapObjectSelection[];
}

class MapObjectSelectionHandler implements Serializable<MapObjectSelectionHandler> {

    viewport: Viewport;

    // selections: MapObjectSelection[] = [];
    availableColors: Color[];

    markerSelectionModeActive: boolean = false;

    private _selectionsByType: { [objectType: string]: MapObjectSelection[]; } = {};

    activeMapObjectType: MapObjectType;
    activeSelectionId: MapObjectSelectionId;

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

    getSelectionsForType(type: string) {
        if (this._selectionsByType[type] == undefined) {
            this._selectionsByType[type] = [];
        }
        return this._selectionsByType[type];
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
        //             if (this.activeSelectionId !== -1) {
        //                 this.clickOnMapObject(clickPos, mapObjectId);
        //             }
        //         });
        //     });
        // });
    }

    addSelection(type: string, sel: MapObjectSelection) {
        this.getSelectionsForType(type).push(sel);
    }

    clickOnMapObject(clickPos: MapPosition, mapObject: MapObject) {
        var sel = this.getActiveSelection();
        if (sel) {
            sel.addMapObjectAt(clickPos, mapObject.id);
        } else {
            console.log('No active selection found');
        }
    }

    getActiveSelection(): MapObjectSelection {
        if (this.activeSelectionId !== -1) {
            return this.getSelection(
                this.activeMapObjectType, this.activeSelectionId
            );
        } else {
            return undefined;
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
        var selections = this.getSelectionsForType(type);
        return _(selections).find((s) => {
            return s.id === selectionId;
        });
    }

    // getSelectedMapObjects(selectionId: MapObjectSelectionId) {
    //     var sel = this.getSelectionById(selectionId);
    //     return sel !== undefined ? sel.getMapObjects() : [];
    // }

    addNewMapObjectSelection(type: string) {
        var id = this.getSelectionsForType(type).length;
        var color = this._getNextColor(type);
        var newSel = new MapObjectSelection(id, type, color);
        this.viewport.map.then((map) => {
            newSel.addToMap(map);
        });
        var selections = this.getSelectionsForType(type);
        selections.push(newSel);
        return newSel;
    }

    private _getNextColor(type: string) {
        var sels = this.getSelectionsForType(type);
        var possibleIds = _.range(this.availableColors.length);
        var usedIds = _(sels).map(function(s) { return s.id; });
        var availableIds = _.difference(possibleIds, usedIds);
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
            this.viewport.map.then((map: ol.Map) => {
                sel.removeFromMap(map);
                var selections = this.getSelectionsForType(sel.mapObjectType);
                selections.splice(selections.indexOf(sel), 1);
            });
        } else {
            console.log('Trying to delete nonexistant selection with id ' + sel.id);
        }
    };

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
                activeSelectionId: this.activeSelectionId,
                selections: selections
            };
            return ser;
        });
    }
}

