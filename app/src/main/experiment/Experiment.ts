interface ISerializable {
    toBlueprint(): Object;
}

interface IWithFromBlueprint {
    fromBlueprint(): ISerializable;
}

interface IFeature {}

interface IExperimentService {
    getFeaturesForExperiment(e: ExperimentId): ng.IPromise<IFeature[]>;
    getCellsForExperiment(e: ExperimentId): ng.IPromise<ICell[]>;
}

type ExperimentId = string;

interface IExperimentArgs {
    id: string;
    name: string;
    description: string;
}

interface IExperiment {
    id: ExperimentId;
    name: string;
    description: string;
}

class Experiment implements IExperiment {
    id: ExperimentId;
    name: string;
    description: string;
    cells: ng.IPromise<{ [cellId: string]: IMapPosition }>;
    features: ng.IPromise<any>;

    constructor(opt: IExperimentArgs,
                private experimentService: IExperimentService,
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

    toBlueprint() {
        return {
            id: this.id,
            name: this.name,
            description: this.description
        };
    }
}

class ExperimentFactory {
    static $inject = ['experimentService', '$q'];
    constructor(private experimentService, private $q) {}

    create(opt: IExperimentArgs): IExperiment {
        return new Experiment(opt, this.experimentService, this.$q);
    }
}

angular.module('tmaps.main.experiment')
.service('ExperimentFactory', ExperimentFactory);
