(function() {
    angular.module('jtui.util', []);
    angular.module('jtui.main', [
        'ngAnimate', 'ui.bootstrap'
    ]);
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
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
    }]);
}());
