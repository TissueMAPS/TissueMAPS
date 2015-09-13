class AppInstanceDeserializer implements Deserializer<AppInstance> {

    static $inject = ['AppInstanceFactory', 'ExperimentDeserializer', '$q'];

    constructor(private appInstanceFty: AppInstanceFactory,
                private experimentDeserializer: ExperimentDeserializer,
                private $q: ng.IQService) {}

    deserialize(ser: SerializedAppInstance) {
        var instDef = this.$q.defer();
        var expPromise = this.experimentDeserializer.deserialize(ser.experiment);
        var exp = expPromise.then((exp) => {
            console.log(this);
            var inst = this.appInstanceFty.create(exp);
            console.log('Inst:', inst);

            inst.addChannelLayers(ser.channelLayerOptions);
            inst.addMaskLayers(ser.maskLayerOptions);

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
