class ExperimentFactory {
    static $inject = ['experimentService', '$q'];
    constructor(private experimentService, private $q) {}

    create(opt: ExperimentArgs): Experiment {
        return new Experiment(opt, this.experimentService, this.$q);
    }
}

angular.module('tmaps.main.experiment')
.service('ExperimentFactory', ExperimentFactory);
