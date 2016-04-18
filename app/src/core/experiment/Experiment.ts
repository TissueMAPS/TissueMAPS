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
    status: string;
}

interface CreateExperimentArgs {
    name: string;
    description: string;
    plateFormat: number;
    microscopeType: string;
    plateAcquisitionMode: string;
}

type ExperimentArgs = SerializedExperiment;


class Experiment {
    id: string;
    name: string;
    description: string;
    channels: Channel[] = [];
    status: string;

    private _mapObjectInfo: {[objectName: string]: MapObjectInfo} = {};

    constructor(args: ExperimentArgs) {

        var $q = $injector.get<ng.IQService>('$q');

        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.status = args.status;

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

    // TODO: error handling
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
        .then((resp: {data: {experiment: SerializedExperiment}}) => {
            return new Experiment(resp.data.experiment);
        });
    }

    // TODO: error handling
    static delete(id: string): ng.IPromise<boolean> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.delete('/api/experiments/' + id)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }

    static create(args: CreateExperimentArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var deferredExp = $q.defer();
        $http.post('/api/experiments', {
            name: args.name,
            description: args.description,
            plate_format: args.plateFormat,
            microscope_type: args.microscopeType,
            plate_acquisition_mode: args.plateAcquisitionMode
        })
        .then((resp: {data: {experiment: SerializedExperiment}}) => {
            deferredExp.resolve(new Experiment(resp.data.experiment));
        })
        .catch((resp) => {
            deferredExp.reject(resp.data.error);
        });
        return deferredExp.promise;
    }

    get workflowDescription() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var deferredExp = $q.defer();
        return $http.get('/api/experiments/' + this.id + '/workflow_description')
        .then((resp: {data: {workflow_description: any}}) => {
            return resp.data.workflow_description;
        })
        .catch((resp) => {
            $q.reject(resp.data.error);
        });
    }

    submitWorkflow(workflowArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.post('/api/experiments/' + this.id + '/workflow', workflowArgs)
        .then((resp) => {
            console.log(resp);
            return resp.data;
        })
        .catch((resp) => {
            $q.reject(resp.data.error);
        });
    }
}
