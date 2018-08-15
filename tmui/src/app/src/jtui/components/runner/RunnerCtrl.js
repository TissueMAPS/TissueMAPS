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
angular.module('jtui.runner')
.controller('RunnerCtrl', ['$scope', '$state', '$stateParams', '$uibModal', '$window', 'hotkeys', 'projectService',
        function ($scope, $state, $stateParams, $uibModal, $window, hotkeys,
            projectService) {

    var currentModuleName = $stateParams.moduleName;
    // Get the current module
    for (i in $scope.project.handles) {
        if ($scope.project.handles[i].name == currentModuleName) {
          // console.log($scope.project)
          var currentModule = $scope.project.handles[i];
          var currentModuleIndex = i;
        }
    }
    $scope.module = currentModule;

    $scope.goToPreviousModule = function () {
        // console.log('current module: ', $scope.module.name)
        var moduleIndex = $scope.project.handles.map(function (e) {
            return e.name;
        }).indexOf($scope.module.name);
        var previousModuleIndex = moduleIndex - 1;
        // console.log('previous module index: ', previousModuleIndex)
        if (previousModuleIndex >= 0 && $scope.project.handles.length > previousModuleIndex) {
            // console.log('go to previous module: ', $scope.project.handles[previousModuleIndex].name)
            $state.go('project.module', {
                moduleName: $scope.project.handles[previousModuleIndex].name
            });
        }
    };

    $scope.goToNextModule = function () {
        // console.log('current module: ', $scope.module.name)
        var moduleIndex = $scope.project.handles.map(function (e) {
            return e.name;
        }).indexOf($scope.module.name);
        var nextModuleIndex = moduleIndex + 1;
        // console.log('next module index: ', nextModuleIndex)
        if (nextModuleIndex >= 0 && $scope.project.handles.length > nextModuleIndex) {
            // console.log('go to next module: ', $scope.project.handles[nextModuleIndex].name)
            $state.go('project.module', {
                moduleName: $scope.project.handles[nextModuleIndex].name
            });
        }
    };

    var logIsOpen = false;
    $scope.showJobLog = function (jobIndex) {
        if (logIsOpen) return;
        var modalInst = $uibModal.open({
            templateUrl: 'src/setup/modals/output.html',
            size: 'lg',
            resolve: {
                title: function () {
                    return 'Log output of job #' + $scope.jobs[jobIndex].id;
                },
                stdout: function () {
                    return $scope.jobs[jobIndex].stdout;
                },
                stderr: function () {
                    return $scope.jobs[jobIndex].stderr;
                }
            },
            controller: 'SetupOutputCtrl',
            controllerAs: 'output'
        });

        logIsOpen = true;

        modalInst.result.then(function () {
            logIsOpen = false;
        }, function () {
            logIsOpen = false;
        });
    };

    var figureIsOpen = false;
    $scope.showFigure = function (jobIndex) {

        if (figureIsOpen) return;

        // TODO: show error dialog when no figure exists
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/runner/modals/figure.html',
            windowClass: 'figure-window',
            // windowTopClass: 'figure-window',
            resolve: {
                figure: ['projectService', function(projectService){
                    return projectService.getModuleFigure(
                            $stateParams.experimentid,
                            $scope.module.name,
                            $scope.jobs[jobIndex].id
                        );
                }],
                name: function () {
                    return $scope.module.name;
                },
                jobId: $scope.jobs[jobIndex].id
            },
            controller: 'FigureCtrl'
        });

        figureIsOpen = true;

        modalInst.result.then(function () {
            figureIsOpen = false;
        }, function () {
            figureIsOpen = false;
        });
    };

    // Define keyboard shortcuts
    hotkeys.bindTo($scope)
    .add({
      combo: ['up', 'k'],
      description: 'go to previous module (upstream in the pipeline)',
      callback: $scope.goToPreviousModule
    })
    .add({
      combo: ['down', 'j'],
      description: 'go to next module (downstream in the pipeline)',
      callback: $scope.goToNextModule
    })
    .add({
      combo: 'o',
      description: 'show log output of current job',
      callback: $scope.showJobLog
    })
    .add({
      combo: 'f',
      description: 'show figure of current module and job',
      callback: $scope.showFigure
    })

    $scope.reportBug = function(){
        $window.open('https://github.com/TissueMAPS/JtLibrary/issues', '_blank');
    };

}]);
