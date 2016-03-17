interface SerializedMapObjectInfo {
    mapobject_type_name: string;
    features: {name: string; }[];
}


interface SerializedExperiment {
    id: string;
    name: string;
    description: string;
    channels: SerializedChannel[];
    mapobject_info: SerializedMapObjectInfo[];
}


type ExperimentArgs = SerializedExperiment;


class Experiment {
    id: string;
    name: string;
    description: string;
    channels: Channel[] = [];

    private _mapObjectInfo: {[objectName: string]: MapObjectInfo} = {};

    constructor(args: ExperimentArgs) {

        var $q = $injector.get<ng.IQService>('$q');

        this.id = args.id;
        this.name = args.name;
        this.description = args.description;

        args.mapobject_info.forEach((i) => {
            this._mapObjectInfo[i.mapobject_type_name] =
                new MapObjectInfo(i.mapobject_type_name, i.features);
        });

        args.channels.forEach((ch) => {
            var isFirstChannel = this.channels.length == 0;
            var channel = new Channel(_.extend(ch, {
                visible: isFirstChannel
            }));
            this.channels.push(channel);
        });
    }

    getMapObjectInfo(objectName: string) {
        return this._mapObjectInfo[objectName];
    }

    get mapObjectNames() {
        return _.keys(this._mapObjectInfo); 
    }

    // serialize(): ng.IPromise<SerializedExperiment> {
    //     var ser: SerializedExperiment = {
    //         id: this.id,
    //         name: this.name,
    //         description: this.description,
    //         channels: this.channels
    //     };
    //     return $injector.get<ng.IQService>('$q').when(ser);
    // }
    get maxZ(): number {
        var zs = this.channels.map((ch) => {
            return ch.maxZ;
        });
        return Math.max.apply(this, zs);
    }

    get minZ(): number {
        var zs = this.channels.map((ch) => {
            return ch.minZ;
        });
        return Math.min.apply(this, zs);
    }

    static getAll(): ng.IPromise<Experiment[]> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/experiments')
        .then((resp: { data: { experiments: SerializedExperiment[]; } }) => {
            var exps = resp.data.experiments;
            return exps.map((e) => {
                return new Experiment(e);
            });
        });
    }

    // TODO: error handling
    static get(id: string): ng.IPromise<Experiment> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/experiments/' + id)
        .then((resp: {data: SerializedExperiment}) => {
            return new Experiment(resp.data);
        });
    }

}
