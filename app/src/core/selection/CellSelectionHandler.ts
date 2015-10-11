interface SerializedSelectionHandler extends Serialized<CellSelectionHandler> {
    activeSelectionId: CellSelectionId;
    selections: SerializedCellSelection[];
}

class CellSelectionHandler implements Serializable<CellSelectionHandler> {

    viewport: Viewport;
    activeSelectionId: CellSelectionId;
    selections: CellSelection[] = [];
    availableColors: Color[];

    constructor(viewport) {

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

    addCellOutlines(cells: Cell[]) {
        window['cells'] = cells;
        var cellLayer = new ObjectLayer('Cells', {
            objects: cells,
            // Upon testing 0.002 was the lowest alpha value which still caused to
            // hitDetection mechanism to find the cell. Lower values get probably floored to 0.
            fillColor: Color.RED.withAlpha(0.002),
            strokeColor: Color.WHITE,
            visible: false
        });
        this.viewport.addObjectLayer(cellLayer);
        this.viewport.map.then((map) => {
            map.on('singleclick', (evt) => {
                map.forEachFeatureAtPixel(evt.pixel, (feat, layer) => {
                    console.log(evt);
                    // FIXME: Maybe we should save the whole mapobject on the feature, or
                    // subclass Feature directly.
                    var cellId = feat.get('name');
                    var clickPos = {x: evt.coordinate[0], y: evt.coordinate[1]};
                    if (this.activeSelectionId !== -1) {
                        this.clickOnCell(clickPos, cellId);
                    }
                });
            });
        });
    }

    addSelection(sel: CellSelection) {
        this.selections.push(sel);
    }

    serialize() {
        var selectionsPr = _(this.selections).map((sel) => { return sel.serialize(); });
        return $injector.get<ng.IQService>('$q').all(selectionsPr).then((selections) => {
            var ser = {
                activeSelectionId: this.activeSelectionId,
                selections: selections
            };
            return ser;
        })
    }

    clickOnCell(clickPos: MapPosition, cellId: CellId) {
        if (this.activeSelectionId !== -1) {
            this.addCellToSelection(clickPos, cellId, this.activeSelectionId);
        }
    }

    addCellToSelection(markerPosition: MapPosition,
                       cellId: CellId,
                       selectionId: CellSelectionId) {
        var selection = this.getSelectionById(selectionId);
        if (selection === undefined) {
            throw new Error('Unknown selection id: ' + selectionId);
        }
        selection.addCell(markerPosition, cellId);
    }

    getSelectionById(selectionId: CellSelectionId) {
        return _(this.selections).find((s) => { return s.id === selectionId; });
    }

    getSelectedCells(selectionId: CellSelectionId) {
        var sel = this.getSelectionById(selectionId);
        return sel !== undefined ? sel.getCells() : [];
    }

    addNewCellSelection() {
        var id = this.selections.length;
        var color = this.getNextColor();
        var newSel = new CellSelection(id, color);
        this.viewport.map.then((map) => {
            newSel.addToMap(map);
        });
        this.selections.push(newSel);
        return newSel;
    }

    private getNextColor() {
        var possibleIds = _.range(this.availableColors.length);
        var usedIds = _(this.selections).map(function(s) { return s.id; });
        var availableIds = _.difference(possibleIds, usedIds);
        if (availableIds.length != 0) {
            var id = availableIds[0];
            return this.availableColors[id];
        } else {
            return this.availableColors[
                this.selections.length % this.availableColors.length
            ];
        }
    }

    removeSelectionById = function(id) {
        var sel = this.getSelectionById(id);
        if (sel) {
            this.viewport.map.then((map: ol.Map) => {
                sel.removeFromMap(map);
                this.selections.splice(this.selections.indexOf(sel), 1);
            });
        } else {
            console.log('Trying to delete nonexistant selection with id ' + id);
        }
    };
}

