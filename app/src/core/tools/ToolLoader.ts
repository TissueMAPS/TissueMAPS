class ToolLoader {
    static $inject = ['$http', '$q', 'toolFactory'];

    constructor(private $http: ng.IHttpService,
                private $q: ng.IQService,
                private toolFactory: ToolFactory) {
    }

    loadTools(appInstance: AppInstance) {
        var toolsDef = this.$q.defer();
        this.$http.get('/src/core/tools/tools.json').then((resp) => {
            var toolsConfig = <any> resp.data;
            var classNames: string[] = toolsConfig.loadClasses;
            console.log(classNames);
            var tools = _.map(classNames, (clsName: string) => {
                var t = this.toolFactory.create(
                    appInstance,
                    clsName
                );
                return t;
            });
            toolsDef.resolve(tools);
        });

        return toolsDef.promise;
    }
}

angular.module('tmaps.core').service('toolLoader', ToolLoader);

