class ToolLoader {
    static $inject = ['$http', '$q', 'ToolFactory'];

    constructor(private $http, private $q, private ToolFactory) {
    }

    loadTools(appInstance: AppInstance) {
        var toolsDef = this.$q.defer();
        this.$http.get('/src/tools/tools.json').then((resp) => {
            var configs = resp.data;
            var tools = _.map(configs, (cfg: any) => {
                if (!cfg.id || !cfg.templateUrl) {
                    throw new Error('No id or templateUrl given for tool with config: ' + cfg);
                } else {
                    var windowCfg = cfg.window || {
                        height: 800,
                        width: 300
                    };
                    var t = this.ToolFactory.create(
                        appInstance,
                        cfg.id,
                        cfg.name || cfg.id,
                        cfg.description || cfg.id,
                        cfg.template,
                        cfg.icon || cfg.id,
                        windowCfg.height,
                        windowCfg.width
                    );

                    return t;
                }
            });
            toolsDef.resolve(tools);
        });

        return toolsDef.promise;
    }
}

angular.module('tmaps.main.tools').service('ToolLoader', ToolLoader);

