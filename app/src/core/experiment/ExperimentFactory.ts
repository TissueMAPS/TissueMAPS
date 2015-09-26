class ExperimentFactory {
    static $inject = ['experimentService', '$q'];
    constructor(private experimentService, private $q) {}

    create(opt: ExperimentArgs): Experiment {
        return new Experiment(opt, this.experimentService, this.$q);
    }

    createFromServerResponse(e: ExperimentAPIObject) {
        var channels = _.map(e.layers, (l) => {
            return {
                name: l.name,
                imageSize: l.imageSize,
                pyramidPath: l.pyramidPath
            };
        });
        return this.create({
            id: e.id,
            name: e.name,
            description: e.description,
            channels: channels
        });
    }
}

angular.module('tmaps.main.experiment')
.service('experimentFactory', ExperimentFactory);
