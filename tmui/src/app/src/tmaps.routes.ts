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
            plates: ['workflowService', 'experiment',
                        (workflowService, experiment) => {
                return experiment.getPlates()
                .then((plates) => {
                    // console.log(plates)
                    return plates;
                });
            }],
            workflow: ['workflowService', 'experiment',
                        (workflowService, experiment) => {
                return workflowService.getWorkflow(experiment)
                .then((workflow) => {
                    // console.log(workflow)
                    return workflow;
                });
            }]
        },
        onEnter: function() {
            console.log('Enter setup');
        }
    })
    .state('setup.upload', {
        url: '/stages/:stageName',
        views: {
            'stage-view': {
                templateUrl: '/src/setup/uploadfiles/uploadfiles.html'
            }
        }
    })
    .state('setup.stage', {
        url: '/stages/:stageName',
        resolve: {
            workflow: ['workflowService', 'experiment', 'plates',
                        (workflowService, experiment, plates) => {
                return workflowService.getWorkflow(experiment)
                .then((workflow) => {
                    // console.log(workflow)
                    return workflow;
                });
            }]

        },
        views: {
            'stage-view': {
                templateUrl: '/src/setup/stage.html',
                controller: 'StageCtrl',
                controllerAs: 'stageCtrl'
            }
        }
    })
    .state('setup.step', {
        parent: 'setup.stage',
        url: '/steps/:stepName',
        resolve: {
            workflow: ['workflowService', 'experiment',
                        (workflowService, experiment) => {
                return workflowService.getWorkflow(experiment)
                .then((workflow) => {
                    return workflow;
                });
            }]

        },
        views: {
            'step-settings-view': {
                templateUrl: '/src/setup/step.html',
                controller: 'StepCtrl',
                controllerAs: 'stepCtrl'
            },
            'step-jobs-view': {
                templateUrl: '/src/setup/jobs.html',
                controller: 'StepCtrl',
                controllerAs: 'stepCtrl'
            }
        }
    })
    .state('plate', {
        parent: 'setup.upload',
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
                var experimentId = $stateParams.experimentid;
                return (new PlateDAO(experimentId)).get(plateId);
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
                var experimentId = $stateParams.experimentid;
                return (new AcquisitionDAO(experimentId)).get(acquisitionId);
            }]
        },
        breadcrumb: {
            class: 'highlight',
            text: 'upload',
            stateName: 'acquisition.detail'
        }
    })
    .state('jtui', {
        url: '/jtui/:experimentid',
        resolve: {
            experiment: getExperiment
        },
        data: {
            loginRequired: true
        },
        parent: 'logo-backdrop',
        templateUrl: '/src/jtui/jtui.html'
    })
    .state('project', {
        parent: 'jtui',
        url: '/project',
        resolve: {
            project: ['experiment', 'projectService', '$stateParams',
                        function(experiment, projectService, $stateParams) {
                        return projectService.getProject(experiment.id);
            }],
            channels: ['experiment', 'projectService', '$stateParams',
                        function(experiment, projectService, $stateParams) {
                        return projectService.getChannels(experiment.id);
            }]
        },
        views: {
            'project': {
                templateUrl: 'src/jtui/components/project/project.html',
                controller: 'ProjectCtrl'
            }
        }
    })
    .state('project.module', {
        url: '/:moduleName',
        views: {
            'handles': {
                templateUrl: 'src/jtui/components/handles/handles.html',
                controller: 'HandlesCtrl'
            },
            'runner': {
                templateUrl: 'src/jtui/components/runner/runner.html',
                controller: 'RunnerCtrl'
            }
        }
    });
}]);

