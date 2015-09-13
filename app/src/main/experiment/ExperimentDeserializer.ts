class ExperimentDeserializer implements Deserializer<Experiment> {

    static $inject = ['ExperimentFactory', '$q'];

    constructor(private experimentFactory: ExperimentFactory,
                private $q: ng.IQService) {}

    deserialize(e: SerializedExperiment) {
        var experiment = this.experimentFactory.create({
            id: e.id,
            name: e.name,
            description: e.description
        });
        return this.$q.when(experiment);
    }
}

angular.module('tmaps.main.experiment').service(
    'ExperimentDeserializer', ExperimentDeserializer
);
