class ToolLoader {
    static $inject = ['$http', '$q'];

    constructor(private $http: ng.IHttpService,
                private $q: ng.IQService) {}

    loadTools(appInstance: AppInstance) {
        var toolsDef = this.$q.defer();
        this.$http.get('/src/core/tools/tools.json').then((resp) => {
            var toolsConfig = <any> resp.data;
            var classNames: string[] = toolsConfig.loadClasses;
            console.log(classNames);
            var tools = _.map(classNames, (clsName: string) => {
                var constr = window[clsName];
                console.log(constr);
                if (constr === undefined) {
                    throw Error('No such tool constructor: ' + clsName);
                } else {
                    var t = new constr(appInstance);
                    return t;
                }
                return t;
            });
            toolsDef.resolve(tools);
        });

        return toolsDef.promise;
    }
}

angular.module('tmaps.core').service('toolLoader', ToolLoader);

