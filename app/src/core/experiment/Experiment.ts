type ExperimentId = string;

interface ExperimentArgs {
    id: string;
    name: string;
    description: string;
    channels: Channel[];
    mapObjectInfo: {[objectName: string]: MapObjectInfo};
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

    private _mapObjectInfo: {[objectName: string]: MapObjectInfo};

    constructor(opt: ExperimentArgs) {

        var $q = $injector.get<ng.IQService>('$q');

        this.id = opt.id;
        this.name = opt.name;
        this.description = opt.description;
        this._mapObjectInfo = opt.mapObjectInfo;

        this.channels = opt.channels;
    }

    getMapObjectInfo(objectName: string) {
        return this._mapObjectInfo[objectName];
    }

    get mapObjectNames() {
        return _.keys(this._mapObjectInfo); 
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

    static getAll(): ng.IPromise<Experiment[]> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/experiments')
        .then((resp: any) => {
            var exps = resp.data.experiments;
            return _.map(exps, Experiment._fromServerResponse);
        });
    }

    // TODO: error handling
    static get(id: ExperimentId): ng.IPromise<Experiment> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/experiments/' + id)
        .then((resp: {data: ExperimentAPIObject}) => {
            return Experiment._fromServerResponse(resp.data);
        });
    }

    static _fromServerResponse(e: ExperimentAPIObject) {
        var channels = _.map(e.layers, (l) => {
            return {
                name: l.name,
                imageSize: l.imageSize,
                pyramidPath: l.pyramidPath
            };
        });
        var mapObjectInfos: {[objectName: string]: MapObjectInfo} = {};
        e.map_object_info.forEach((info) => {
            mapObjectInfos[info.map_object_name] =
                new MapObjectInfo(info.map_object_name, info.features);
        });
        return new Experiment({
            id: e.id,
            name: e.name,
            description: e.description,
            channels: channels,
            mapObjectInfo: mapObjectInfos
        });
    }
}
