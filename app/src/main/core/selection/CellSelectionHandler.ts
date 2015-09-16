interface SerializedSelectionHandler extends Serialized<CellSelectionHandler> {
    activeSelectionId: CellSelectionId;
    selections: SerializedCellSelection[];
}

class CellSelectionHandler implements Serializable<CellSelectionHandler> {

    appInstance: AppInstance;
    activeSelectionId: CellSelectionId;
    selections: CellSelection[] = [];
    availableColors: Color[];

    constructor(private colorFactory: ColorFactory,
                private cellSelectionFty: CellSelectionFactory,
                private $q: ng.IQService,
                private $http: ng.IHttpService,
                private $rootScope: ng.IRootScopeService,
                appInstance) {

        this.appInstance = appInstance;

        var colorsRGBString = [
            'rgb(228,26,28)','rgb(55,126,184)','rgb(77,175,74)','rgb(152,78,163)',
            'rgb(255,127,0)','rgb(255,255,51)','rgb(166,86,40)','rgb(247,129,191)',
            'rgb(153,153,153)'
        ];
        this.availableColors = _(colorsRGBString).map((rgb) => {
            return this.colorFactory.createFromRGBString(rgb);
        });

    }

    addSelection(sel: CellSelection) {
        this.selections.push(sel);
    }

    serialize() {
        var selectionsPr = _(this.selections).map((sel) => { return sel.serialize(); });
        return this.$q.all(selectionsPr).then((selections) => {
            var ser = {
                activeSelectionId: this.activeSelectionId,
                selections: selections
            };
            return ser;
        })
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
        var newSel = this.cellSelectionFty.create(id, color);
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
            sel.removeFromMap(this.appInstance.map);
            this.selections.splice(this.selections.indexOf(sel), 1);
        } else {
            console.log('Trying to delete nonexistant selection with id ' + id);
        }
    };
}

