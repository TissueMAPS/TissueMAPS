angular.module('tmaps.ui')
.value('lastUsed', {
    experiment: null,
    viewer: null
})
.config(['$stateProvider', '$urlRouterProvider', '$locationProvider',
             function($stateProvider, $urlRouterProvider, $locationProvider) {

    // For any unmatched url redirect to root
    $urlRouterProvider.otherwise('/login');

    var getExperiment = ['$stateParams', '$state', 'lastUsed', '$q',
                           ($stateParams, $state, lastUsed, $q) => {
        var experimentId = $stateParams.experimentid;
        var wasExperimentIdSupplied =
            experimentId !== undefined && experimentId !== '';
        if (wasExperimentIdSupplied) {
            return (new ExperimentDAO()).get(experimentId)
            .then((exp) => {
                lastUsed.experiment = exp;
                return exp;
            })
            .catch((err) => {
                $state.go('userpanel');
            });
        } else if (lastUsed.experiment) {
            return lastUsed.experiment;
        } else {
            return $q.reject().catch(() => {
                $state.go('userpanel');
            });
        }
    }];

    $stateProvider
    .state('viewer', {
        url: '/viewer/:experimentid',
        reloadOnSearch: false,
        views: {
            'main-window': { template: '' }
        },
        data: {
            loginRequired: true
        },
        resolve: {
            'experiment': getExperiment
        },
        onEnter: ['application', 'experiment',
                  function(app, experiment) {
            var viewerToBeShown = _(app.viewers).find((viewer) => {
                return viewer.experiment.id === experiment.id;
            });
            var viewerToBeShownExists = viewerToBeShown !== undefined;
            if (viewerToBeShownExists) {
                app.showViewer(viewerToBeShown);
            } else {
                var newViewer = new Viewer(experiment);
                app.addViewer(newViewer);
                app.showViewer(newViewer);
            }
        }],
        onExit: ['application', function(app) {
            app.hide();
        }]
    })
    .state('logo-backdrop', {
        abstract: true,
        views: {
            'logo-backdrop': {
                template: 
                  '<ui-view></ui-view>' +
                  '<div class="logo-container">' +
                    '<img width=400 height=400 src="/resources/img/tmaps_logo.png" alt=""/>' +
                  '</div>'
            }
        }
    })
    .state('content', {
        parent: 'logo-backdrop',
        abstract: true,
        template: '<div class="content-view container" ui-view></div>'
    })
    .state('login', {
        parent: 'logo-backdrop',
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
        templateUrl: '/src/userpanel/userpanel.html',
        redirectTo: 'userpanel.experiment.list'

    })
    .state('userpanel.experiment', {
        url: '/experiments',
        views: {
            'userpanel-main': { template: '<ui-view></ui-view>' }
        },
        abstract: true,
    })
    .state('userpanel.experiment.list', {
        url: '',
        templateUrl: '/src/userpanel/experiment.list.html'
    })
    .state('userpanel.experiment.create', {
        url: '/create',
        templateUrl: '/src/userpanel/experiment.create.html',
        controller: 'CreateExperimentCtrl',
        controllerAs: 'createExpCtrl'
    })
    .state('setup', {
        parent: 'content',
        url: '/setup/:experimentid',
        data: {
            loginRequired: true
        },
        templateUrl: '/src/setup/setup.html',
        controller: 'SetupCtrl',
        controllerAs: 'setupCtrl',
        resolve: {
            experiment: getExperiment,
            plates: ['$http', 'experiment', '$state', '$q',
                     ($http, experiment, $state, $q) => {
                var def = $q.defer();
                (new PlateDAO()).getAll({
                    experiment_id: experiment.id
                }).then((plates) => {
                    def.resolve(plates);
                })
                .catch((error) => {
                    $state.go('userpanel');
                    def.reject(error);
                })
                return def.promise;
            }]
        },
        onEnter: function() {
            console.log('Enter setup');
        }
    })
    .state('setup.uploadfiles', {
        url: '/stages/uploadfiles',
        views: {
            'stage-view': {
                templateUrl: '/src/setup/uploadfiles/uploadfiles.html'
            }
        },
    })
    .state('setup.stage', {
        url: '/stages/:stageName',
        views: {
            'stage-view': {
                templateUrl: '/src/setup/stage.html',
                controller: 'StageCtrl',
                controllerAs: 'stageCtrl'
            }
        },
        resolve: {
            'stage': ['experiment', '$stateParams', (experiment, $stateParams) => {
                var stage = _.find(experiment.workflowDescription.stages, (st: any) => {
                    return st.name === $stateParams.stageName;
                });
                if (stage !== undefined) {
                    return stage;
                } else {
                    return {
                        name: 'uploadfiles'
                    };
                }
            }]
        }
    })
    .state('plate', {
        parent: 'setup.uploadfiles',
        url: '/plates',
        templateUrl: '/src/setup/uploadfiles/plate.html',
        controller: 'PlateListCtrl',
        controllerAs: 'plateListCtrl',
        breadcrumb: {
            // class: 'highlight',
            text: 'plates',
            stateName: 'plate'
        }
    })
    .state('plate.create', {
        url: '/create',
        templateUrl: '/src/setup/uploadfiles/plate.create.html',
        controller: 'PlateCreateCtrl',
        controllerAs: 'createCtrl',
        breadcrumb: {
            class: 'highlight',
            text: 'create plate',
            stateName: 'plate.create'
        }
    })
    .state('plate.detail', {
        url: '/:plateid',
        templateUrl: '/src/setup/uploadfiles/plate.detail.html',
        controller: 'PlateDetailCtrl',
        controllerAs: 'plateDetailCtrl',
        resolve: {
            plate: ['$http', '$stateParams', ($http, $stateParams) => {
                var plateId = $stateParams.plateid;
                return (new PlateDAO()).get(plateId);
            }]
        },
        breadcrumb: {
            class: 'highlight',
            text: 'plate',
            stateName: 'plate.detail'
        }
    })
    .state('acquisition', {
        abstract: true,
        parent: 'plate.detail',
        url: '/acquisitions',
        template: '<ui-view></ui-view>',
    })
    .state('acquisition.create', {
        url: '/create',
        templateUrl: '/src/setup/uploadfiles/acquisition.create.html',
        controller: 'AcquisitionCreateCtrl',
        controllerAs: 'createCtrl',
        breadcrumb: {
            class: 'highlight',
            text: 'create acquisition',
            stateName: 'acquisition.create'
        }
    })
    .state('acquisition.detail', {
        url: '/:acquisitionid',
        templateUrl: '/src/setup/uploadfiles/acquisition.detail.html',
        controller: 'AcquisitionDetailCtrl',
        controllerAs: 'acquisitionDetailCtrl',
        resolve: {
            acquisition: ['$stateParams', function($stateParams) {
                var acquisitionId = $stateParams.acquisitionid;
                return (new AcquisitionDAO()).get(acquisitionId);
            }]
        },
        breadcrumb: {
            class: 'highlight',
            text: 'upload',
            stateName: 'acquisition.detai'
        }
    });

}]);

