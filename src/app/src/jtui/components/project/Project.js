angular.module('jtui.project')
.factory('Project', [function() {

    function Project(experiment_id, name, pipe, handles) {
        this.experiment_id = experiment_id;
        this.name = name;
        this.pipe = pipe;
        this.handles = handles;
    }
    return Project;
}]);
