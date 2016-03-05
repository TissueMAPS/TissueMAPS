class MapObjectInfo {
    mapObjects: ng.IPromise<MapObject[]>;

    constructor(public mapObjectName: string,
                public features: Feature[]) {
        var $http = $injector.get<ng.IHttpService>('$http');
        $http.get('')
    }
}
