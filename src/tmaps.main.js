(function() {
    /**
     * Declare all modules here.
     * In the index this file is listed right after all library code (incl. angular)
     * and after the shared module, but before all other application modules.
     * => Make sure to never redeclare a module in another file
     * (i.e. never call an already declared module with an array argument).
     */
    angular.module('tmaps.core', []);
    angular.module('tmaps.mock.core', []);
    angular.module('tmaps.core.layer', []);
    angular.module('tmaps.core.selection', ['tmaps.core.layer', 'tmaps.shared.services']);
    angular.module('tmaps.core', [
        'tmaps.shared.thirdpartymodules',
        'tmaps.core.selection',
        'tmaps.shared.services',
        'tmaps.core.layer'
    ]);

    angular.module('tmaps.main.misc', []);

    angular.module('tmaps.main.layerprops', [
        'ui.slider',
        'ui.bootstrap',
        'tmaps.main.misc'
    ]);

    angular.module('tmaps.main.layerprops.channels', ['tmaps.main.layerprops']);
    angular.module('tmaps.main.layerprops.masks', ['tmaps.main.layerprops']);
    angular.module('tmaps.main.layerprops.selections', ['tmaps.main.layerprops']);

    angular.module('tmaps.main.experiment', []);
    angular.module('tmaps.mock.main.experiment', []);

    angular.module('tmaps.main.appstate', [
        'ui.router',
        'tmaps.main.dialog'
    ]);
    angular.module('tmaps.mock.main.appstate', []);

    angular.module('tmaps.main.user', [
        'ui.router',
        'tmaps.main.appstate',
        'tmaps.main.experiment',
        'ui.bootstrap'
    ]);

    angular.module('tmaps.main.tools', ['tmaps.main.appstate']);

    angular.module('tmaps.main.auth', [
        'ui.bootstrap'
    ]);

    angular.module('tmaps.main.dialog', [
        'ui.bootstrap'
    ]);

    // Declare the main module.
    // Make sure to list third party angular modules here after their code
    // has been put into the `libs` directory.
    var tmaps = angular.module('tmaps.main', [
        'tmauth',

        // Shared
        'tmaps.shared',

        // Application code
        'tmaps.main.misc',

        'tmaps.core',
        'tmaps.core.selection',
        'tmaps.core.layer',

        'tmaps.main.misc',

        'tmaps.main.experiment',
        'tmaps.main.appstate',
        'tmaps.main.user',

        'tmaps.main.tools',

        'tmaps.main.layerprops.channels',
        'tmaps.main.layerprops.masks',
        'tmaps.main.layerprops.selections',

        // 'tmaps.main.auth',

        'tmaps.main.dialog',

        // Thirdparty code
        'ui.router',
        'ngSanitize',

        'ui.bootstrap',
        'ui.sortable',
        'ui.slider',

        'perfect_scrollbar',
        'ngColorPicker',

        'ngWebsocket'
    ]);

    tmaps.config(['$httpProvider', function($httpProvider) {
        $httpProvider.interceptors.push('authInterceptor');
    }]);


    tmaps.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
                 function($stateProvider, $urlRouterProvider, $locationProvider) {

        // For any unmatched url redirect to root
        $urlRouterProvider.otherwise('/welcome');

        $stateProvider
        .state('content', {
            abstract: true,
            templateUrl: '/templates/main/content.html',
        })
        .state('welcome', {
            parent: 'content',
            url: '/welcome',
            templateUrl: '/templates/main/welcome.html',
            data: {
                loginRequired: false
            },
            onEnter: ['application', function(app) {
                app.hideViewport();
            }]
        })
        .state('viewport', {
            url: '/viewport?loadex=expids&state=stateid&snapshot=snapshotid',
            reloadOnSearch: false,
            onEnter: ['application', '$stateParams', 'experimentService', 'appstateService',
                      function(app, $stateParams, experimentService, appstateService) {

                app.showViewport();

                // Check if the app should load an app state
                var stateID = $stateParams.state;
                var snapshotID = $stateParams.snapshot;

                if (angular.isDefined(stateID)) {
                    appstateService.loadStateFromId(stateID);
                } else if (angular.isDefined(snapshotID)) {
                    appstateService.loadSnapshotFromId(snapshotID);
                } else {
                    //
                }

                // Check if some experiments should be added
                var experimentIDs = $stateParams.loadex;
                if (angular.isDefined(experimentIDs)) {
                    _(experimentIDs.split(',')).each(function(experimentID) {
                        experimentService.getExperiment(experimentID).success(function(exp) {
                            app.addExperiment(exp);
                        });
                    });
                }
            }],
            onLeave: ['application', function(app) {
                app.hideViewport();
            }]
        })
        .state('viewport.userpanel', {
            url: '/userpanel',
            data: {
                loginRequired: true
            },
            onEnter: ['userpanelService', function(userpanelService) {
                userpanelService.showPanel();
            }],
            onExit: ['userpanelService', function(userpanelService) {
                userpanelService.hidePanel();
            }]
        })
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

    }]);


}());
