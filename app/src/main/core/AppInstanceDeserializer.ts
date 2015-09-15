class AppInstanceDeserializer implements Deserializer<AppInstance> {

    static $inject = [
        'CellSelectionDeserializer', 'CellSelectionHandlerFactory',
        'AppInstanceFactory', 'ExperimentDeserializer', '$q'
    ];

    constructor(private cellSelectionDeserializer: CellSelectionDeserializer,
                private cellSelectionHandlerFty: CellSelectionHandlerFactory,
                private appInstanceFty: AppInstanceFactory,
                private experimentDeserializer: ExperimentDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedAppInstance) {

        var instDef = this.$q.defer();

        // Deserialize the experiment object related to this app instance first.
        var expPromise = this.experimentDeserializer.deserialize(ser.experiment);

        var exp = expPromise.then((exp) => {
            var inst = this.appInstanceFty.create(exp);

            // Create and initialize the selection handler
            var selHandler = this.cellSelectionHandlerFty.create(inst);
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
            inst.addChannelLayers(ser.channelLayerOptions);
            inst.addMaskLayers(ser.maskLayerOptions);

            // Recover map state
            inst.map.then(function(map) {
                var v = map.getView();
                v.setZoom(ser.mapState.zoom);
                v.setCenter(ser.mapState.center);
                v.setResolution(ser.mapState.resolution);
                v.setRotation(ser.mapState.rotation);

                // TODO: Add serialization of selectionhandler
                // inst.selectionHandler.initFromBlueprint(bp.selectionHandler);
                instDef.resolve(inst);
            });
        });

        return instDef.promise;
    }
}

angular.module('tmaps.core').service('AppInstanceDeserializer', AppInstanceDeserializer);
