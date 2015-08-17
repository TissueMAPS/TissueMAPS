// TODO: Put this file in a location that can be concatted into both script.js
// files. Name the module tmaps.shared or something
angular.module('tmaps.shared.services')
.factory('toolConfigs', ['$http', '$q', function($http, $q) {

    function generateSlug(toolId) {
        return toolId.toLowerCase().replace(/[^A-Za-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
    }

    var configsDef = $q.defer();

    // TODO: Change location so that it can easily be copied to the production dir
    // 'src' isn't copied to dist/
    $http.get('/src/tools/tools.json').then(function(resp) {
        var cfg = resp.data;
        var configs = _.map(resp.data, function(toolCfg) {
            if (!toolCfg.id || !toolCfg.templateUrl) {
                throw new Error('No id or templateUrl given for tool with config: ' + cfg);
            } else {
                toolCfg.slug = generateSlug(toolCfg.id);
            }
            return toolCfg;
        });
        configsDef.resolve(configs);
    });

    return {
        configs: configsDef.promise,

        generateSlug: generateSlug,

        getConfigForSlug: function(toolSlug) {
            return this.configs.then(function(cfgs) {
                var result = _.find(cfgs, function(cfg) {
                    return cfg.slug == toolSlug;
                });
                if (!result) {
                    var slugs = _.map(cfgs, function(cfg) { return cfg.slug; });
                    throw new Error(
                        'No tool in tools.json has a name that matched the slug:' + toolSlug +
                        'The slugs in the system are: ' + slugs
                    );
                } else {
                    return result;
                }
            });
        }
    };
}]);
