class ExperimentService {
    static $inject = ['$http', '$q'];

    constructor(private $http: ng.IHttpService, private $q) {}

    getAvailableExperiments(): ng.IPromise<Experiment[]> {
        return this.$http
        .get('/api/experiments')
        .then((resp) => {
            return resp.data;
        });
    }

    // TODO: error handling
    getExperiment(id: ExperimentId): ng.IPromise<Experiment> {
        return this.$http
        .get('/api/experiments/' + id)
        .success((data, headers) => {
            return data;
        });
    }

    // TODO: error handling
    // TODO: more general approach for different objects getObjectsForExample()
    // getCellsForExperiment(id: ExperimentId): ng.IPromise<Cell[]> {
    //     var def = this.$q.defer();
    //     if (this.cachedCells[id] !== undefined) {
    //         return this.$q.when(this.cachedCells[id]);
    //     }
    //     this.$http.get('/api/experiments/' + id + '/cells')
    //     .success((data) => {
    //         var cells = [];
    //         // Convert from string => [float, float] map
    //         // to int => [float, float]
    //         for (var id in data) {
    //             var coord = data[id];
    //             var updCoord = _(coord).map((c) => {
    //                 // The first element in c corresponds to the
    //                 // i coordinate, whereas the second is the j
    //                 // coordinate. TissueMAPS works with (x, y) coordinates instead,
    //                 // where the y axis is inverted (origin in the topleft corner).
    //                 return [c[1], -1 * c[0]];
    //             });

    //             var sumX = 0;
    //             var sumY = 0;

    //             var i;
    //             var nCoord = coord.length;
    //             for (i = 0; i < nCoord; i++ ){
    //                 sumX += coord[i][1];
    //                 sumY += coord[i][0];
    //             }
    //             sumY *= -1;
    //             var meanX = sumX / nCoord;
    //             var meanY = sumY / nCoord;
    //             var centroid = {
    //                 x: meanX,
    //                 y: meanY
    //             };

// //                 updCoord = [[
// //                     updCoord[0],
// //                     updCoord[Math.round(updCoord.length * 0.25)],
// //                     updCoord[Math.round(updCoord.length * 0.50)],
// //                     updCoord[Math.round(updCoord.length * 0.75)],
// //                     updCoord[updCoord.length - 1]
// //                 ]];

    //             var cell = new this.Cell(id, centroid, updCoord);

    //             cells.push(cell);
    //         }
    //         this.cachedCells[id] = cells;
    //         def.resolve(cells);
    //     })
    //     .error((err) => {
    //         def.reject('Error while retreiving cells');
    //     });
    //     return def.promise;
    // }
}

/**
 * A service that concerns itself with querying the server
 * for experiments and prompting to user when he wants to add an experiment
 * to the viewport.
 */
angular.module('tmaps.core').service('experimentService', ExperimentService);
