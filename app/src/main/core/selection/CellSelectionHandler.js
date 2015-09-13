angular.module('tmaps.core.selection')
.factory('CellSelectionHandler',
         ['CellSelection', '$q', '_', 'selectionColorMap', '$http',
             '$rootScope',
         function(CellSelection, $q, _, selectionColorMap, $http, $rootScope) {

    function CellSelectionHandler(appInstance) {
        var self = this;

        this.selections = [];
        this.map = appInstance.map;
        this.appInstance = appInstance;

        window.cell = this;

        // TODO: Don't save active selection id on
        // TODO: This should maybe be done via draw interactions etc.
        // that are created on the selectionlayer object
        // E.g. click on the "Select selection"
        var getActiveSelectionId = function() {
            return self.activeSelectionId;
        };

        this.map.then(function(map) {
            map.on('singleclick', function(evt) {
                var x = evt.coordinate[0];
                var y = evt.coordinate[1];
                var selectionId = getActiveSelectionId();
                // If there is a selection active, if none is selected
                // selectionId will be -1.
                if (angular.isDefined(selectionId)) {
                    var selection = self.getSelectionById(selectionId);
                    // Try to get the cell id for
                    self.appInstance.getCellAtPos(x, y)
                    .then(function(cellId) {
                        if (cellId) {
                            $rootScope.$broadcast('clickedOnCell', {
                                cellId: cellId
                            });
                        }
                        if (cellId && selection.isCellSelected(cellId)) {
                            selection.removeCell(cellId);
                        } else if (cellId) {
                            // self.appstate.cellPositions
                            // .then(function(cellPositions) {
                            //     var pos = cellPositions[cellId];
                            //     if (pos) {
                            //         return pos;
                            //     } else {
                                    // return [x, y];
                                // }
                            // })
                            // .then(function(position) {
                            var position = {x: x, y: y};
                                self.addCellToSelection(position, cellId, selectionId);
                            // });
                        } else {
                            console.log('no cell at pos: ' + [x, y]);
                        }
                    });
                }
            });
        });
    }

    CellSelectionHandler.prototype.addCellToSelection = function(markerPosition, cellId, selectionId) {
        var selection = this.getSelectionById(selectionId);

        if (!selection) {
            throw new Error('Unknown selection id: ' + selectionId);
        }

        selection.addCell(markerPosition, cellId);
    };

    CellSelectionHandler.prototype.getSelectedCells = function(selectionId) {
        var sel = this.getSelectionById(selectionId);
        return sel ? sel.getCells() : [];
    };

    CellSelectionHandler.prototype.getSelectionById = function(selectionId) {
        return _(this.selections).find(function(s) { return s.id === selectionId; });
    };

    CellSelectionHandler.prototype.addNewCellSelection = function() {
        var id = this.generateSelectionId();
        if (id !== false) {
            var newSel = new CellSelection(this.map, id);
            this.selections.push(newSel);
            return newSel;
        } else {
            console.log('No more available colors, cannot create new selection.');
            return undefined;
        }
    };

    CellSelectionHandler.prototype.generateSelectionId = function() {
        var possibleIds = selectionColorMap.getMappableIds();
        var usedIds = _(this.selections).map(function(s) { return s.id; });
        var availableIds = _.difference(possibleIds, usedIds);
        return availableIds.length != 0 ? availableIds[0] : false;
    };

    CellSelectionHandler.prototype.removeSelectionById = function(id) {
        var sel = this.getSelectionById(id);
        if (sel) {
            sel.destroy();
            this.selections.splice(this.selections.indexOf(sel), 1);
        } else {
            console.log('Trying to delete nonexistant selection with id ' + id);
        }
    };

    CellSelectionHandler.prototype.toBlueprint = function() {
        return {
            activeSelectionId: this.activeSelectionId,
            selections: this.selections.map(function(s) { return s.toBlueprint(); })
        };
    };

    CellSelectionHandler.prototype.initFromBlueprint = function(bp) {
        var self = this;
        bp.selections.forEach(function(selectionBp) {
            var newSel = new CellSelection.fromBlueprint(self.map, selectionBp);
            self.selections.push(newSel);
        });
        if (angular.isDefined(bp.activeSelectionId)) {
            this.activeSelectionId = bp.activeSelectionId;
        }
    };

    return CellSelectionHandler;
}]);
