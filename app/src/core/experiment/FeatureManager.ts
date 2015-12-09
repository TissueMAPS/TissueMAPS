type FeatureMap = { [objectType: string]: Feature[]; };

interface FeaturesServerResponse {
    features: FeatureMap;
}

class FeatureManager {

    experiment: Experiment;

    private _featuresByType: ng.IPromise<FeatureMap>;
    private _$q: ng.IQService;

    getFeaturesForType(t: MapObjectType) {
        return this._featuresByType.then((map) => {
            return map[t];
        });
    }

    constructor(experiment: Experiment) {
        this.experiment = experiment;
        var $q = $injector.get<ng.IQService>('$q');
        var featuresByTypeDef = $q.defer();
        this._featuresByType = featuresByTypeDef.promise;
        this._fetchFeatures(this.experiment, featuresByTypeDef);
    }

    private _fetchFeatures(exp: Experiment, def: ng.IDeferred<FeatureMap>) {
        var $http = $injector.get<ng.IHttpService>('$http');
        $http.get('/api/experiments/' + exp.id + '/features').success((data: FeaturesServerResponse) => {
            // TODO: Change structure
            def.resolve(data.features);
        }).error((err) => {
            def.reject(err);
        });
    }

}
