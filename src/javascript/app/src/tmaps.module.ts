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

        'perfect_scrollbar',

        'ngColorPicker',
        'ngSanitize',
        'ngWebsocket',

        'jtui'
    ]);

    tmaps.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
    }]);

    tmaps.run(['$injector', function($injector) {
        window['$injector'] = $injector;
    }]);

    // Run this code after all providers have been registered
    tmaps.run(['$rootScope', 'authService', 'loginDialogService', '$state', 'application', '$websocket',
              function($rootScope, authService, loginDialogService, $state, application, $websocket) {

        /**
         * Check if the user is trying to transition to a state that requires
         * authentication (i.e. the state's data object includes
         * 'loginRequired === true'). If yes, then prompt the user with a login
         * dialog before proceeding.
         */
        $rootScope.$on('$stateChangeStart',
                       function(event, toState, toParams, fromState, fromParams) {

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
        });


        // Add a redirectTo property to states
        $rootScope.$on('$stateChangeStart', (evt, to, params) => {
            if (to.redirectTo) {
                evt.preventDefault();
                $state.go(to.redirectTo, params);
            }
        });

    }]);

}());
