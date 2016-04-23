interface SerializedPlate {
    id: string;
    name: string;
    description: string;
    experiment_id: string;
    acquisitions: SerializedAcquisition[];
}

interface PlateArgs {
    id: string;
    name: string;
    description: string;
    acquisitions: Acquisition[];
}

interface CreatePlateArgs {
    name: string;
    description: string;
}

class Plate {

    id: string;
    name: string;
    description: string;
    acquisitions: Acquisition[];

    constructor(args: PlateArgs) {
        this.id = args.id;
        this.name = args.name;
        this.description = args.description;
        this.acquisitions = args.acquisitions;
    }

    static getAll(experimentId: string): ng.IPromise<Plate[]> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/experiments/' + experimentId + '/plates')
        .then((resp: { data: { plates: SerializedPlate[]; } }) => {
            var plates = resp.data.plates;
            return plates.map((p) => {
                return Plate.fromJSON(p);
            });
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }

    static fromJSON(data: SerializedPlate) {
        return new Plate({
            id: data.id,
            name: data.name,
            description: data.description,
            acquisitions: data.acquisitions.map((acq) => {
                return Acquisition.fromJSON(acq);
            })
        });
    }

    // TODO: error handling
    static delete(id: string): ng.IPromise<boolean> {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.delete('/api/plates/' + id)
        .then((resp) => {
            return true;
        })
        .catch((resp) => {
            return resp.data.error;
        });
    }

    static get(id: string) {
        var $http = $injector.get<ng.IHttpService>('$http');
        return $http.get('/api/plates/' + id)
        .then((resp: {data: {plate: SerializedPlate;}}) => {
            return Plate.fromJSON(resp.data.plate);
        })
        .catch((resp) => {
            return resp.data.error;
        })
    }

    static create(experimentId: string, args: CreatePlateArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var def = $q.defer();
        $http.post('/api/experiments/' + experimentId + '/plates', args)
        .then((resp: {data: {plate: SerializedPlate}}) => {
            def.resolve(Plate.fromJSON(resp.data.plate));
        })
        .catch((resp) => {
            def.reject(resp.data.error);
        });
        return def.promise;
    }

    get isReadyForProcessing() {
        var hasMinOneAcquisition = this.acquisitions.length > 0; 
        var allAcquisitionsReady = _.all(this.acquisitions.map((aq) => {
            return aq.status === 'COMPLETE';
        }));
        return hasMinOneAcquisition && allAcquisitionsReady;
    }
}
