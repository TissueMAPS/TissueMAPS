angular.module('tmaps.ui')
.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
             function($stateProvider, $urlRouterProvider, $locationProvider) {

    // For any unmatched url redirect to root
    $urlRouterProvider.otherwise('/login');

    $stateProvider
    .state('viewer', {
        // url: '/viewer?loadex=expids&state=stateid&snapshot=snapshotid',
        url: '/viewer/:experimentid',
        reloadOnSearch: false,
        views: {
            'main-window': { template: '' }
        },
        data: {
            loginRequired: true
        },
        onEnter: ['application', '$stateParams', '$state', 
                  function(app, $stateParams, $state) {

            // Check if some experiments should be added
            var experimentId = $stateParams.experimentid;
            var wasExperimentIdSupplied =
                experimentId !== undefined && experimentId !== '';
            if (wasExperimentIdSupplied) {
                var viewerToBeShown = _(app.viewers).find((viewer) => {
                    return viewer.experiment.id === experimentId;
                });
                var viewerToBeShownExists = viewerToBeShown !== undefined;
                if (viewerToBeShownExists) {
                    app.showViewer(viewerToBeShown);
                } else {
                    Experiment.get(experimentId).then(function(exp) {
                        var newViewer = new Viewer(exp);
                        app.addViewer(newViewer);
                        app.showViewer(newViewer);
                    });
                }
            } else {
                var availableViewers = app.viewers;
                if (availableViewers.length > 0)  {
                    app.showViewer(availableViewers[0]);
                } else {
                    $state.go('userpanel');
                }
            }
            // Check if the app should load an app state
            //var stateID = $stateParams.state;
            //var snapshotID = $stateParams.snapshot;

            //if (angular.isDefined(stateID)) {
            //    appstateService.loadStateFromId(stateID);
            //} else if (angular.isDefined(snapshotID)) {
            //    appstateService.loadSnapshotFromId(snapshotID);
            //} else {
            //    //
            //}

            // Check if some experiments should be added
            // var experimentIDs = $stateParams.loadex;
            // if (angular.isDefined(experimentIDs)) {
            //     _(experimentIDs.split(',')).each(function(experimentID) {
            //         Experiment.get(experimentID).then(function(exp) {
            //             app.addExperiment(exp);
            //         });
            //     });
            // }
        }],
        onExit: ['application', function(app) {
            app.hide();
        }]
    })
    .state('content', {
        abstract: true,
        views: {
            'content-view': {
                template: 
                  '<div class="content-view" ui-view></div>' +
                  '<div class="logo-container">' +
                    '<img width=400 height=400 src="/resources/img/tmaps_logo.png" alt=""/>' +
                  '</div>'
            }
        }
    })
    .state('login', {
        parent: 'content',
        url: '/login',
        templateUrl: '/src/auth/login.html',
        data: {
            loginRequired: false
        },
    })
    .state('userpanel', {
        parent: 'content',
        url: '/userpanel',
        data: {
            loginRequired: true
        },
        templateUrl: '/src/userpanel/userpanel.html'
    })
    .state('setup', {
        parent: 'content',
        url: '/setup',
        data: {
            loginRequired: true
        },
        templateUrl: '/src/setup/setup.html'
    });

}]);

