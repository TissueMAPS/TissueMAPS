// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
(function() {
    angular.module('jtui.main', [
        'ngAnimate', 'ui.bootstrap', 'perfect_scrollbar'
    ]);
    angular.module('jtui.handles', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'perfect_scrollbar', 'ngSanitize'
    ]);
    angular.module('jtui.project', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'ui.sortable', 'ngDraggable', 'cfp.hotkeys', 'smart-table',
        'checklist-model', 'xeditable', 'perfect_scrollbar'  // 'jtui.main',
    ]);
    angular.module('jtui.module', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ui.bootstrap',
        'ui.sortable', 'ngDraggable', 'cfp.hotkeys', 'perfect_scrollbar'
    ]);
    angular.module('jtui.runner', [
        'ngAnimate', 'angular-loading-bar', 'ui.router', 'ngWebsocket',
        'perfect_scrollbar', 'cfp.hotkeys', 'plotly', 'hc.marked' // 'hljs',
    ]);

    var jtui = angular.module('jtui', [
        'ui.router',
        'ngWebsocket',
        'ngAnimate',
        'angular-loading-bar',
        'ui.sortable',
        'ui.bootstrap',
        'smart-table',
        'ngDraggable',
        'ngSanitize',
        'cfp.hotkeys',
        'checklist-model',
        'xeditable',
        'jtui.main',
        'jtui.project',
        'jtui.module',
        'jtui.handles',
        'jtui.runner',
        'perfect_scrollbar',
        // 'hljs',
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

    jtui.run(['$rootScope', '$state', '$stateParams', 'editableOptions',
             function($rootScope, $state, $stateParams, editableOptions){
        $rootScope.$state = $state;
        $rootScope.$stateParams = $stateParams;
        editableOptions.theme = 'bs3';
    }]);
}());
