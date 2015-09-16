class ExperimentFactory {
    static $inject = ['experimentService', '$q'];
    constructor(private experimentService, private $q) {}

    create(opt: ExperimentArgs): Experiment {
        return new Experiment(opt, this.experimentService, this.$q);
    }

    createFromServerResponse(e: ExperimentAPIObject) {
        return this.create({
            id: e.id,
            name: e.name,
            description: e.description
        });
    }
}

angular.module('tmaps.main.experiment')
.service('experimentFactory', ExperimentFactory);
