angular.module('jtui.module')
.factory('Module', [function() {

    function Module(name, description, pipeline) {
        this.name = name;
        this.description = description;
        this.pipeline = pipeline;
    }
    return Module;
}]);
