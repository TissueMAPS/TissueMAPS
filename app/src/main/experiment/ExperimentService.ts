class ExperimentService {
    static $inject = ['$modal', '$http'];

    constructor(private $modal, private $http: ng.IHttpService) {}

    getAvailableExperiments(): ng.IPromise<Experiment[]> {
        return this.$http
        .get('/api/experiments')
        .then(function(resp) {
            return resp.data;
        });
    }

    // TODO: error handling
    getExperiment(id: ExperimentId): ng.IPromise<Experiment> {
        return this.$http
        .get('/api/experiments/' + id)
        .success(function(data, headers) {
            return data;
        });
    }

    // TODO: error handling
    getFeaturesForExperiment(id: ExperimentId): ng.IPromise<Feature[]> {
        return this.$http.get('/api/experiments/' + id + '/features?include=min,max')
        .then(function(resp: any) {
            return resp.data.features;
        });
    }

    // TODO: error handling
    getCellsForExperiment(id: ExperimentId): ng.IPromise<Cell[]> {
        return this.$http.get('/api/experiments/' + id + '/cells')
        .success(function(data) {
            var cells = [];
            // Convert from string => [float, float] map
            // to int => [float, float]
            _(data).each(function(position, id) {
                cells.push({
                    id: id,
                    centroid: position
                });
            });
            return cells;
        })
        .error(function(err) {
            console.log('Error while retreiving cells');
        });
    }
}

/**
 * A service that concerns itself with querying the server
 * for experiments and prompting to user when he wants to add an experiment
 * to the viewport.
 */
angular.module('tmaps.main.experiment').service('experimentService', ExperimentService);
