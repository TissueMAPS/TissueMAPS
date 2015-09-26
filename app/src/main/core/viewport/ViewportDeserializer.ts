class ViewportDeserializer implements Deserializer<Viewport> {

    static $inject = [
        'cellSelectionDeserializer', 'cellSelectionHandlerFactory',
        'viewportFactory', 'experimentDeserializer', '$q'
    ];

    constructor(private cellSelectionDeserializer: CellSelectionDeserializer,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private viewportFty: ViewportFactory,
                private experimentDeserializer: ExperimentDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedViewport) {

        var vpDef = this.$q.defer();

        // Deserialize the experiment object related to this viewport first.
        var expPromise = this.experimentDeserializer.deserialize(ser.experiment);

        var exp = expPromise.then((exp) => {
            var vp = this.viewportFty.create(exp);

            // Create and initialize the selection handler
            var selHandler = this.cellSelectionHandlerFty.create(vp);
            var activeSelId = ser.selectionHandler.activeSelectionId;
            var selections = ser.selectionHandler.selections;
            selections.forEach((serializedSelection) => {
                var newSel = this.cellSelectionDeserializer.deserialize(serializedSelection);
                newSel.then((sel) => {
                    selHandler.addSelection(sel);
                })
            });
            if (activeSelId !== undefined) {
                selHandler.activeSelectionId = activeSelId;
            }

            // Add layers
            vp.addChannelLayers(ser.channelLayerOptions);
            vp.addMaskLayers(ser.maskLayerOptions);

            // Recover map state
            vp.map.then(function(map) {
                var v = map.getView();
                v.setZoom(ser.mapState.zoom);
                v.setCenter(ser.mapState.center);
                v.setResolution(ser.mapState.resolution);
                v.setRotation(ser.mapState.rotation);

                // TODO: Add serialization of selectionhandler
                // vp.selectionHandler.initFromBlueprint(bp.selectionHandler);
                vpDef.resolve(vp);
            });
        });

        return vpDef.promise;
    }
}

angular.module('tmaps.core').service('viewportDeserializer', ViewportDeserializer);
