(function() {
    /**
     * Declare all tool modules here.
     */
    angular.module('tmaps.tools', []);

    angular.module('tmaps.tools.util', []);

    angular.module('tmaps.tools.widgets', [
        'ui.slider',
        'tmaps.shared.color',
        'tmaps.tools.util'
    ]);

    angular.module('tmaps.tools.modules.svm', []);
    angular.module('tmaps.tools.modules.decisiontree', []);
    angular.module('tmaps.tools.modules.featurestats', []);
    angular.module('tmaps.tools.modules.cellstats', []);
    angular.module('tmaps.tools.modules.cluster', []);
    angular.module('tmaps.tools.modules.filter', []);

    /**
     * After declaring a tool module above, add it to this module's dependencies
     * so that everything is loaded when the tool-subapp is initialized by
     * angular.
     */
    var tmapsToolsModules = angular.module('tmaps.tools.modules', [
        'tmaps.tools.widgets',
        'tmaps.tools.modules.svm',
        'tmaps.tools.modules.decisiontree',
        'tmaps.tools.modules.featurestats',
        'tmaps.tools.modules.cellstats',
        'tmaps.tools.modules.cluster',
        'tmaps.tools.modules.filter'
    ]);

    // Declaration of tools module
    var tmapsTools = angular.module('tmaps.tools', [
        'tmaps.shared',

        'tmaps.tools.util',
        'tmaps.tools.widgets',
        'tmaps.tools.modules',

        'ui.router',
        'ngSanitize',

        'ui.bootstrap',
        'ui.sortable',
        'ui.slider',

        'perfect_scrollbar',
        'ngColorPicker',
        'highcharts-ng',

        'ngWebsocket'
    ]);

    tmapsTools.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
    }]);

    tmapsTools.config(['$stateProvider', function($stateProvider) {
        $stateProvider
        .state('tool', {
            url: '/:slug',
            templateUrl: '/templates/tools/tool-content.html',
            controller:  'ToolContentCtrl',
            resolve: {
                toolConfig: ['toolConfigs', '$stateParams',
                             function(toolConfigs, $stateParams) {
                    var toolSlug = $stateParams.slug;
                    return toolConfigs.getConfigForSlug(toolSlug);
                }]
            }
        });
    }]);

    tmapsTools.run(['$rootScope', '$window', function($rootScope, $window) {

        if (!angular.isDefined($window.init)) {
            console.log(
                'There is no global TissueMAPS helper object for this tool window! ' +
                'The tool won\'t function properly!'
            );
        }

    }]);

}());

