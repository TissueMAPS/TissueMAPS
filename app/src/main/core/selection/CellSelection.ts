type CellSelectionId = number;

class CellSelection implements Serializable<CellSelection> {

    name: string;
    id: CellSelectionId;
    color: Color;
    layer: SelectionLayer;
    cells: { [cellId: string]: MapPosition; } = {};

    constructor(private $q: ng.IQService,
                private ol,
                private selectionLayerFactory: SelectionLayerFactory,
                private $rootScope: ng.IRootScopeService,

                id: CellSelectionId,
                color: Color) {

        this.id = id;
        this.color = color;
        this.name = 'Selection #' + id;

        this.layer = this.selectionLayerFactory.create(this.name, this.color);
    }

    addToMap(map: ol.Map) {
        this.layer.addToMap(map);
    }

    getCells() {
        var cellIds = _.chain(this.cells)
                       .keys()
                       .map(function(k) { return parseInt(k); })
                       .value();
        return cellIds;
    }

    removeFromMap(map: ol.Map) {
        // Somehow the markers won't get removed when removing the layer
        // and clear needs to be called beforehand.
        this.clear();
        this.layer.removeFromMap(map);
    }

    removeCell(cellId: CellId) {
        if (this.cells.hasOwnProperty(cellId)) {
            this.layer.removeCellMarker(cellId);
            delete this.cells[cellId];
        };
        this.$rootScope.$broadcast('cellSelectionChanged', this);
    }

    /**
     * Remove all cells from this selection, but don't delete it.
     */
    clear() {
        // TODO: Consider doing this via some batch mechanism if it proves to be slow
        _.keys(this.cells).forEach((cellId: string) => {
            this.removeCell(cellId);
        });
        this.$rootScope.$broadcast('cellSelectionChanged', this);
    }

    addCell(markerPos: MapPosition, cellId: CellId) {
        if (this.cells.hasOwnProperty(cellId)) {
            return;
        } else {
            this.cells[cellId] = markerPos;
            this.layer.addCellMarker(cellId, markerPos);
        }
        this.$rootScope.$broadcast('cellSelectionChanged', this);
    }

    isCellSelected(cell: Cell) {
        return this.cells[cell.id] !== undefined;
    }

    serialize() {
        var ser = {
            id: this.id,
            cells: this.cells,
            color: this.color.serialize()
        }
        return this.$q.when(ser);
    }

}


interface SerializedCellSelection extends Serialized<CellSelection> {
    id: CellSelectionId;
    cells: { [cellId: string]: MapPosition; };
    color: SerializedColor;
}


class CellSelectionFactory {

    static $inject = [
        '$q',
        'openlayers',
        'selectionLayerFactory',
        '$rootScope'
    ];

    constructor(private $q: ng.IQService,
                private ol,
                private selectionLayerFactory: SelectionLayerFactory,
                private $rootScope: ng.IRootScopeService) {}

    create(id: CellSelectionId, color: Color) {
        return new CellSelection(
            this.$q,
            this.ol,
            this.selectionLayerFactory,
            this.$rootScope,
            id,
            color
        );
    }
}

angular.module('tmaps.core.selection').service('cellSelectionFactory', CellSelectionFactory);
