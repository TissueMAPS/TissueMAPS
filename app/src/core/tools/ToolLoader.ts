class ToolLoader {
    static $inject = ['$http', '$q'];

    constructor(private $http: ng.IHttpService,
                private $q: ng.IQService) {}

}

angular.module('tmaps.core').service('toolLoader', ToolLoader);

