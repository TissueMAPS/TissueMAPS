// angular.module('tmaps.core.selection')
// .factory('CellSelection',
//          ['selectionColorMap', 'openlayers', 'SelectionLayer', '$rootScope',
//          function(selectionColorMap, ol, SelectionLayer, $rootScope) {

//     function CellSelection(map, id) {
//         this.map = map;
//         this.id = id;
//         this.name = 'Selection #' + this.id;

//         // A map from cellId to map positions
//         this.cells = {};

//         this.color = selectionColorMap.getColorForId(this.id);

//         this.layer = new SelectionLayer(this.color);
//         this.map.then(function(map) {
//             this.layer.addToMap(map);
//         }.bind(this));
//     }

//     CellSelection.prototype.getColor = function() {
//         return this.color;
//     };

//     CellSelection.prototype.getCells = function() {
//         var cellIds = _.chain(this.cells)
//                        .keys()
//                        .map(function(k) { return parseInt(k); })
//                        .value();
//         return cellIds;
//     };

//     CellSelection.prototype.destroy = function() {
//         // Somehow the markers won't get removed when removing the layer
//         // and clear needs to be called beforehand.
//         this.clear();
//         this.map.then(function(map) {
//             this.layer.removeFromMap(map);
//         }.bind(this));
//     };

//     CellSelection.prototype.removeCell = function(cellId) {
//         if (this.cells.hasOwnProperty(cellId)) {
//             this.layer.removeCellMarker(cellId);
//             delete this.cells[cellId];
//         };
//         $rootScope.$broadcast('cellSelectionChanged', this);
//     };

//     /**
//      * Remove all cells from this selection, but don't delete it.
//      */
//     CellSelection.prototype.clear = function() {
//         // TODO: Consider doing this via some batch mechanism if it proves to be slow
//         _.keys(this.cells).forEach(function(cellId) {
//             this.removeCell(cellId);
//         }.bind(this));
//         $rootScope.$broadcast('cellSelectionChanged', this);
//     };
//     CellSelection.prototype.addCell = function(markerPos, cellId) {
//         if (this.cells.hasOwnProperty(cellId)) {
//             return;
//         } else {
//             this.cells[cellId] = markerPos;
//             this.layer.addCellMarker(cellId, markerPos);
//         }
//         $rootScope.$broadcast('cellSelectionChanged', this);
//     };

//     CellSelection.prototype.isCellSelected = function(cellId) {
//         return this.cells[cellId] !== undefined;
//     };

//     CellSelection.prototype.toBlueprint = function() {
//         return {
//             id: this.id,
//             cells: this.cells
//         };
//     };

//     CellSelection.fromBlueprint = function(mapPromise, bp) {
//         var sel = new CellSelection(mapPromise, bp.id);
//         _(bp.cells).each(function(markerPos, cellId) {
//             sel.addCell(markerPos, cellId);
//         });
//         return sel;
//     };

//     return CellSelection;
// }]);
