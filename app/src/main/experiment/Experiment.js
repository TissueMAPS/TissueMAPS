angular.module('tmaps.main.experiment')
.factory('Experiment', ['experimentService', '$q',
         function(experimentService, $q) {

    function Experiment(opt) {
        this.id = opt.id;
        this.name = opt.name;
        this.description = opt.description;

        var featuresDef = $q.defer();
        experimentService.getFeaturesForExperiment(this.id)
        .then(function(feats) {
            featuresDef.resolve(feats);
        });
        this.features = featuresDef.promise;

        var cellsDef = $q.defer();
        experimentService.getCellsForExperiment(this.id)
        .then(function(cells) {
            cellsDef.resolve(cells);
        });
        this.cells = cellsDef.promise;
    }

    Experiment.prototype.toBlueprint = function() {
        return {
            id: this.id,
            name: this.name,
            description: this.description
        };
    };

    return Experiment;

}]);

