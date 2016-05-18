(function() {
    angular.module('jtui.util', []);
    angular.module('jtui.main', []);
    angular.module('jtui.topbar', [
        'ngAnimate', 'angular-loading-bar', 'jtui.project', 
        'ui.router', 'cfp.hotkeys', 'ui.bootstrap'
    ]);
    angular.module('jtui.handles', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'perfect_scrollbar', 'ngSanitize'
    ]);
    angular.module('jtui.project', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'ui.sortable', 'ngDraggable', 'cfp.hotkeys', 'smart-table',
        'checklist-model', 'xeditable', 'jtui.main', 'perfect_scrollbar'
    ]);
    angular.module('jtui.module', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'ui.sortable', 'ngDraggable', 'cfp.hotkeys', 'perfect_scrollbar'
    ]);
    angular.module('jtui.runner', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ngWebsocket',
        'perfect_scrollbar', 'cfp.hotkeys', 'plotly', 'hljs', 'hc.marked'
    ]);

    var jtui = angular.module('jtui', [
        'ui.router',
        'ngWebsocket',
        'angular-loading-bar',
        'ngAnimate',
        'ui.sortable',
        'ui.bootstrap',
        'smart-table',
        'ngDraggable',
        'ngSanitize',
        'cfp.hotkeys',
        'checklist-model',
        'xeditable',
        'jtui.util',
        'jtui.main',
        'jtui.topbar',
        'jtui.project',
        'jtui.module',
        'jtui.handles',
        'jtui.runner',
        'perfect_scrollbar',
        'hljs',
        'hc.marked',
        'plotly'
    ]);

    jtui.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
    }]);

    jtui.config(['markedProvider', function(markedProvider) {
        markedProvider.setOptions({
          gfm: true,
          tables: true,
          highlight: function (code, lang) {
            if (lang) {
              return hljs.highlight(lang, code, true).value;
            } else {
              return hljs.highlightAuto(code).value;
            }
          }
        });
    }]);

    jtui.run(['$rootScope', '$state', '$stateParams',
             function($rootScope, $state, $stateParams){

        // It's very handy to add references to $state and $stateParams to the $rootScope
        // so that you can access them from any scope within your applications.
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
    }]);

    jtui.config(['$stateProvider', '$urlRouterProvider',
                function($stateProvider, $urlRouterProvider) {

        // For any unmatched url, send to /
        $urlRouterProvider.otherwise('/');

        $stateProvider
        .state('project', {
            parent: 'jtui',
            // abstract: true,
            // Urls can have parameters. They can be specified like :param or {param}.
            // If {} is used, then you can also specify a regex pattern that the param
            // must match. The regex is written after a colon (:). Note: Don't use capture
            // groups in your regex patterns, because the whole regex is wrapped again
            // behind the scenes. Our pattern below will only match numbers with a length
            // between 1 and 4.
            // url: '/{experimentID}/{subexperimentID:(?:/[^/]+)?}/{projectName}/?',
            url: '/:experimentID/:projectName',

            onExit: function() {
                console.log('exit project state');
            },
            // Use `resolve` to resolve any asynchronous controller dependencies
            // *before* the controller is instantiated. In this case, since project
            // returns a promise, the controller will wait until it is
            // resolved before instantiation. Non-promise return values are considered
            // to be resolved immediately.
            resolve: {
                project: ['projectService', '$stateParams',
                            function (projectService, $stateParams) {

                            return projectService.getProject(
                                        $stateParams.experimentID,
                                        $stateParams.projectName);
                }],
                channels: ['projectService', '$stateParams',
                            function (projectService, $stateParams) {

                            return projectService.getChannels(
                                        $stateParams.experimentID);
                }],
            },
            views: {
                'project': {
                    templateUrl: 'components/project/project.html',
                    controller: 'ProjectCtrl'
                }
            }
        })
        .state('project.module', {
            url: '/:moduleName',
            views: {
                'handles': {
                    templateUrl: 'components/handles/handles.html',
                    controller: 'HandlesCtrl'
                },
                'runner': {
                    templateUrl: 'components/runner/runner.html',
                    controller: 'RunnerCtrl'
                }
            },
            onEnter: function () {}
        });
    }]);
}());
