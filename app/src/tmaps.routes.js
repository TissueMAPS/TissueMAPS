angular.module('tmaps.ui')
.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
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
            app.hideViewports();
        }]
    })
    .state('viewport', {
        url: '/viewport?loadex=expids&state=stateid&snapshot=snapshotid',
        reloadOnSearch: false,
        onEnter: ['application', '$stateParams', 'experimentService', 'appstateService',
                  function(app, $stateParams, experimentService, appstateService) {

            app.showViewports();

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
            app.hideViewports();
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
    });
}]);

