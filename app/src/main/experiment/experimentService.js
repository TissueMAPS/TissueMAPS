angular.module('tmaps.main.experiment')
/**
 * A service that concerns itself with querying the server
 * for experiments and prompting to user when he wants to add an experiment
 * to the viewport.
 */
.service('experimentService',
         ['$modal', '$http',
             function($modal, $http) {

    // TODO: error handling
    this.getAvailableExperiments = function() {
        return $http
        .get('/api/experiments')
        .then(function(resp) {
            return resp.data;
        });
    };

    // TODO: error handling
    this.getExperiment = function(id) {
        return $http
        .get('/api/experiments/' + id)
        .success(function(data, headers) {
            return data;
        });
    };

    // TODO: error handling
    this.getFeaturesForExperiment = function(id) {
        return $http.get('/api/experiments/' + id + '/features?include=min,max')
        .then(function(resp) {
            return resp.data.features;
        });
    };

    // TODO: error handling
    this.getCellsForExperiment = function(experimentId) {
        return $http.get('/api/experiments/' + experimentId + '/cells')
        .then(function(resp) {
            var data = resp.data;
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
        .catch(function(err) {
            console.log('Error while retreiving cells: ', err.status);
        });
    };

}]);
