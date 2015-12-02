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
    features: ng.IPromise<any>;

    constructor(opt: ExperimentArgs) {

        var $q = $injector.get<ng.IQService>('$q');
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

    static fromServerResponse(e: ExperimentAPIObject) {
        var channels = _.map(e.layers, (l) => {
            return {
                name: l.name,
                imageSize: l.imageSize,
                pyramidPath: l.pyramidPath
            };
        });
        return new Experiment({
            id: e.id,
            name: e.name,
            description: e.description,
            channels: channels
        });
    }
}
