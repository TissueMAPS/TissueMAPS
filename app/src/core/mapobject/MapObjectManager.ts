type MapObjectMap = { [objectType: string]: { [objectId: number]: MapObject}; };

interface MapObjectTypeResponse {
    ids: number[];
    visual_type: string;
    map_data: any;
}
interface MapObjectsServerResponse {
    objects: { [type: string]: MapObjectTypeResponse };
}

class MapObjectManager {

    mapObjectsByType: ng.IPromise<MapObjectMap>;
    experiment: Experiment;

    private _mapObjectsByTypeDef: ng.IDeferred<MapObjectMap>;
    private _$q: ng.IQService;

    constructor(experiment: Experiment) {
        this.experiment = experiment;

        this._$q = $injector.get<ng.IQService>('$q');
        this._mapObjectsByTypeDef = this._$q.defer();
        this.mapObjectsByType = this._mapObjectsByTypeDef.promise;
        this._fetchMapObjects(experiment);
    }

    getMapObjectsForType(t: MapObjectType): ng.IPromise<MapObject[]> {
        var def = this._$q.defer();
        this.mapObjectsByType.then((objs) => {
            if (objs[t] === undefined) {
                def.reject('No map objects for this type');
            } else {
                def.resolve(objs[t]);
            }
        });
        return def.promise;
    }

    get mapObjectTypes(): ng.IPromise<string[]> {
        return this.mapObjectsByType.then((map) => {
            return _.keys(map);
        });
    }

    getMapObjectsById(type: MapObjectType,
                      ids: MapObjectId[]): ng.IPromise<MapObject[]> {
        return this.mapObjectsByType.then((objs) => {
            var foundObjects = [];
            _(ids).each((id) => {
                console.log(id);
                var o = objs[type][id];
                if (o !== undefined) {
                    foundObjects.push(o);
                }
            })
            return foundObjects;
        });
    }

    private _fetchMapObjects(e: Experiment) {
        var $http = $injector.get<ng.IHttpService>('$http');
        $http.get('/api/experiments/' + e.id + '/objects')
        .success((resp: MapObjectsServerResponse) => {
            var objs: MapObjectMap = {};
            var responseInterpreter = new MapObjectResponseInterpreter();
            for (var t in resp.objects) {
                objs[t] = {};
                // The response for some specific type
                var responseForType = resp.objects[t];
                // Get an array of map objects for this response
                var mapObjects = responseInterpreter.getObjectsForResponse(responseForType);
                // Add each of those objects to the object map
                _(mapObjects).each((o) => {
                    objs[t][o.id] = o;
                });
            }
            this._mapObjectsByTypeDef.resolve(objs);
        })
        .error((err) => {
            this._mapObjectsByTypeDef.reject(err);
        });
    }
}
