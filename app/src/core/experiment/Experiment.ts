interface Feature {}

type ExperimentId = string;

interface ExperimentArgs {
    id: string;
    name: string;
    description: string;
    channels: Channel[];
}

interface SerializedExperiment extends Serialized<Experiment> {
    id: ExperimentId;
    name: string;
    description: string;
    channels: Channel[];
}

interface Channel {
    name: string;
    imageSize: ImageSize;
    pyramidPath: string;
}

class Experiment implements Serializable<Experiment> {
    id: ExperimentId;
    name: string;
    description: string;
    // TODO: Move this property into a new extending class.
    channels: Channel[];
    cells: ng.IPromise<Cell[]>;
    cellMap: ng.IPromise<{ [cellId: number]: Cell }>;
    features: ng.IPromise<any>;

    constructor(opt: ExperimentArgs,
                private experimentService: ExperimentService,
                private $q: ng.IQService) {

        var $q = $injector.get<IQService>('$q');
        var expService = $injector.get<ExperimentService>('experimentService');

        this.id = opt.id;
        this.name = opt.name;
        this.description = opt.description;

        this.channels = opt.channels;

        var featuresDef = $q.defer();
        expService.getFeaturesForExperiment(this.id)
        .then(function(feats) {
            featuresDef.resolve(feats);
        });
        this.features = featuresDef.promise;

        this.cells = expService.getCellsForExperiment(this.id);
        this.cellMap = this.cells.then((cells) => {
            var map = {};
            var nCells = cells.length;
            for (let i = 0; i < nCells; i++) {
                map[cells[i].id] = cells[i];
            }
            return map;
        });
    }

    serialize(): ng.IPromise<SerializedExperiment> {
        var ser: SerializedExperiment = {
            id: this.id,
            name: this.name,
            description: this.description,
            channels: this.channels
        };
        return $injector.get<ng.IQService>('$q').when(ser);
    }
}
