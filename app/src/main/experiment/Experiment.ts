interface Feature {}

type ExperimentId = string;

interface ExperimentArgs {
    id: string;
    name: string;
    description: string;
}

interface SerializedExperiment extends Serialized<Experiment> {
    id: ExperimentId;
    name: string;
    description: string;
}

class Experiment implements Serializable<Experiment> {
    id: ExperimentId;
    name: string;
    description: string;
    cells: ng.IPromise<{ [cellId: string]: MapPosition }>;
    features: ng.IPromise<any>;

    constructor(opt: ExperimentArgs,
                private experimentService: ExperimentService,
                private $q: ng.IQService) {
        this.id = opt.id;
        this.name = opt.name;
        this.description = opt.description;

        var featuresDef = $q.defer();
        experimentService.getFeaturesForExperiment(this.id)
        .then(function(feats) {
            featuresDef.resolve(feats);
        });
        this.features = featuresDef.promise;

        var cellsDef = $q.defer();
        experimentService.getCellsForExperiment(this.id)
        .then(function(cells) {
            cellsDef.resolve(cells);
        });
        this.cells = cellsDef.promise;
    }

    serialize() {
        return this.$q.when({
            id: this.id,
            name: this.name,
            description: this.description
        });
    }
}
