angular.module('tmaps.core.selection')
.factory('SelectionLayer',
         ['openlayers', '_',
         function(ol, _) {

    function SelectionLayer(color) {
        if (!color) {
            throw new Error('SelectionLayer needs a color with which to colorize the markers!');
        }

        this.color = color;
        this.cellMarkers = {};

        // TODO: Maybe the size of the marker icon should be
        // changed according to the current resolution
        var styleFunc = function(feature, resolution) {
            // resolutiton
            var size = 42; // Compute via resolution
            var colorRgbString = color.toRGBString();
            var imageSrc =
                'resources/img/marker/marker-' + colorRgbString + '-' + size +'.png';
            var style = new ol.style.Style({
                image: new ol.style.Icon({
                    // the bottom of the marker should point to the cell's
                    // center
                    anchor: [0.5, 0.9],
                    src: imageSrc
                })
            });
            return [style];
        };

        this.layer = new ol.layer.Vector({
            source: new ol.source.Vector(),
            style: styleFunc
        });
    }

    SelectionLayer.prototype.addToMap = function(map) {
        map.addLayer(this.layer);
    };

//     SelectionLayer.prototype.startDraw = function() {
//         var action = new ol.interaction.Draw({
//             features: this.overlay.getFeatures(),
//             type: 'Point'
//         });
//         this.map.addInteraction(action);
//         this.currentAction = action;
//     };

    // SelectionLayer.prototype.stopCurrentAction = function() {
    //     if (this.currentAction) {
    //         this.map.removeInteraction(this.currentAction);
    //     }
    // };

    SelectionLayer.prototype.addCellMarker = function(cellId, position) {
        if (!this.cellMarkers.hasOwnProperty(cellId)) {
            var feat = new ol.Feature({
                geometry: new ol.geom.Point([position.x, position.y])
            });
            this.layer.getSource().addFeature(feat);
            this.cellMarkers[cellId] = feat;
        }
    };

    SelectionLayer.prototype.removeCellMarker = function(cellId) {
        var feat = this.cellMarkers[cellId];
        if (feat) {
            this.layer.getSource().removeFeature(feat);
            delete this.cellMarkers[cellId];
        }
    };

    SelectionLayer.prototype.removeFromMap = function(map) {
        map.removeLayer(this.layer);
    };

    return SelectionLayer;

}]);


