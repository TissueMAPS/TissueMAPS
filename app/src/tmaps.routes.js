angular.module('tmaps.ui')
.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
             function($stateProvider, $urlRouterProvider, $locationProvider) {

    // For any unmatched url redirect to root
    $urlRouterProvider.otherwise('/login');

    $stateProvider
    .state('login', {
        url: '/login',
        views: {
            'main-window': {
                templateUrl: '/src/auth/login.html'
            }
        },
        data: {
            loginRequired: false
        },
    })
    .state('viewer', {
        url: '/viewer?loadex=expids&state=stateid&snapshot=snapshotid',
        reloadOnSearch: false,
        views: {
            'main-window': { template: '' }
        },
        onEnter: ['application', '$stateParams', 'appstateService',
                  function(app, $stateParams, appstateService) {

            app.show();

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
                    Experiment.get(experimentID).then(function(exp) {
                        app.addExperiment(exp);
                    });
                });
            }
        }],
        onExit: ['application', function(app) {
            app.hide();
        }]
    })
    .state('userpanel', {
        url: '/userpanel',
        data: {
            loginRequired: true
        },
        views: {
            'main-window': {
                templateUrl: '/src/userpanel/userpanel.html'
            }
        }
    })
    .state('setup', {
        url: '/setup',
        data: {
            loginRequired: true
        },
        views: {
            'main-window': {
                templateUrl: '/src/setup/setup.html'
            }
        }
    });

}]);

