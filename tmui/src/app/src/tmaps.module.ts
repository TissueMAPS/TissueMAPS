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
    // Modules
    angular.module('tmaps.auth', [
        'ngAnimate', 'ui.bootstrap'
    ]);

    /**
     * Declare all modules here.
     * => Make sure to never redeclare a module in another file
     * (i.e. never call an already declared module with an array argument).
     */
    angular.module('tmaps.toolwindow', []); // TODO: remove this
    angular.module('tmaps.core', [
        'ngAnimate', 'ui.bootstrap',
        'tmaps.auth'
    ]);

    angular.module('tmaps.ui', [
        'ngAnimate',
        'tmaps.core',
        'ui.slider',
        'ui.bootstrap',
        'ui.router',
        'tmaps.auth',
        'ngFileUpload',
        'angular-loading-bar',
        'ui.router.breadcrumbs'
    ]);

    // Declare the main module.
    var tmaps = angular.module('tmaps', [
        'ngAnimate',
        'tmaps.core',
        'tmaps.ui',
        'tmaps.toolwindow',  // TODO: remove this

        'tmaps.auth',

        // Thirdparty code
        'ui.router',
        'ui.bootstrap',
        'ui.sortable',
        'ui.slider',
        'ui.scroll',

        'angular-loading-bar',
        'perfect_scrollbar',

        'ngColorPicker',
        'ngSanitize',
        'ngWebsocket',

        'jtui'
    ]);

    tmaps.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
        $httpProvider.interceptors.push('errorInterceptor');
    }]);

    tmaps.run(['$injector', function($injector) {
        window['$injector'] = $injector;
    }]);

    // Run this code after all providers have been registered
    tmaps.run(['$rootScope', 'authService', 'loginDialogService', 'waitingDialogService' , '$state', 'application', '$websocket',
              function($rootScope, authService, loginDialogService, waitingDialogService, $state, application, $websocket) {

        /**
         * Check if the user is trying to transition to a state that requires
         * authentication (i.e. the state's data object includes
         * 'loginRequired === true'). If yes, then prompt the user with a login
         * dialog before proceeding.
         */
        $rootScope.$on('$stateChangeStart', (event, toState, toParams, fromState, fromParams) => {

            var loginRequired = toState.data && toState.data.loginRequired;

            if (loginRequired && !authService.isAuthenticated()) {
                event.preventDefault();

                // $state.go('login');

                loginDialogService.showDialog()
                .then(function(user) {
                    // Login was successful, proceed with state transition.
                    return $state.go(toState.name, toParams);
                })
                .catch(function(err) {
                    // Dialog was dismissed and no login happened,
                    // don't proceed with state transition.
                });
            }
            else {
                // Indicate that data is loaded for state change
                // TODO: Fix loading bar
                // $rootScope.loadingDialog = waitingDialogService.show('Loading');
            }
        });


        // Add a redirectTo property to states
        $rootScope.$on('$stateChangeStart', (evt, to, params) => {
            if (to.redirectTo) {
                evt.preventDefault();
                $state.go(to.redirectTo, params);
            }
        });

        // $rootScope.$on('$stateChangeSuccess', (evt, to, params) => {
        //     $rootScope.loadingDialog.close();
        // });

    }]);

}());
