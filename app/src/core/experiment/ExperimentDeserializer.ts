class ExperimentDeserializer implements Deserializer<Experiment> {

    static $inject = ['experimentFactory', '$q'];

    constructor(private experimentFactory: ExperimentFactory,
                private $q: ng.IQService) {}

    deserialize(e: SerializedExperiment) {
        var experiment = this.experimentFactory.create({
            id: e.id,
            name: e.name,
            description: e.description,
            channels: e.channels
        });
        return this.$q.when(experiment);
    }
}

angular.module('tmaps.main.experiment').service(
    'experimentDeserializer', ExperimentDeserializer
);
