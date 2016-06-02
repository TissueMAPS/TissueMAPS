angular.module('jtui.runner')
.controller('RunnerCtrl', ['$scope', '$state', '$stateParams', '$uibModal', '$window', '$sce', 'hotkeys',
        function ($scope, $state, $stateParams, $uibModal, $window, $sce, hotkeys) {

    var currentModuleName = $stateParams.moduleName;
    // Get the current module
    for (i in $scope.project.handles) {
        if ($scope.project.handles[i].name == currentModuleName) {
          console.log($scope.project)
          var currentModule = $scope.project.handles[i];
          var currentModuleIndex = i;
          var filename = $scope.project.pipe.description.pipeline[i].source;
          var extension = filename.split('.').pop();
          if (extension == 'py') {
            currentModule.language = 'python';
          } else if (extension == 'm') {
            currentModule.language = 'matlab';
          } else if (extension == 'r' | extension == 'R') {
            currentModule.language = 'r';
          } else if (extension == 'jl') {
            currentModule.language = 'julia';
          }
          currentModule.filename = filename;
        }
    }
    $scope.module = currentModule;
    console.log('module: ', currentModule)

    $scope.goToPreviousModule = function () {
        console.log('current module: ', $scope.module.name)
        var moduleIndex = $scope.project.handles.map(function (e) {
            return e.name;
        }).indexOf($scope.module.name);
        var previousModuleIndex = moduleIndex - 1;
        console.log('previous module index: ', previousModuleIndex)
        if (previousModuleIndex >= 0 && $scope.project.handles.length > previousModuleIndex) {
            console.log('go to previous module: ', $scope.project.handles[previousModuleIndex].name)
            $state.go('project.module', {
                moduleName: $scope.project.handles[previousModuleIndex].name
            });
        }
    };

    $scope.goToNextModule = function () {
        console.log('current module: ', $scope.module.name)
        var moduleIndex = $scope.project.handles.map(function (e) {
            return e.name;
        }).indexOf($scope.module.name);
        var nextModuleIndex = moduleIndex + 1;
        console.log('next module index: ', nextModuleIndex)
        if (nextModuleIndex >= 0 && $scope.project.handles.length > nextModuleIndex) {
            console.log('go to next module: ', $scope.project.handles[nextModuleIndex].name)
            $state.go('project.module', {
                moduleName: $scope.project.handles[nextModuleIndex].name
            });
        }
    };

    var outputIsOpen = false;
    $scope.showOutput = function () {
        if (outputIsOpen) return;
        var jobIndex = $scope.jobs.output.map(function (e) {
            return e.id;
        }).indexOf($scope.jobs.currentId);
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/runner/modals/output.html',
            size: 'lg',
            // windowClass: 'modal-window',
            resolve: {
                output: function () {
                    for (j in $scope.jobs.output[jobIndex].modules) {
                        if ($scope.jobs.output[jobIndex].modules[j].name == currentModuleName) {
                            return $scope.jobs.output[jobIndex].modules[j]
                        }
                    }
                }
            },
            controller: 'OutputCtrl'
        });

        outputIsOpen = true;

        modalInst.result.then(function () {
            outputIsOpen = false;
        }, function () {
            outputIsOpen = false;
        });
    };

    var logIsOpen = false;
    $scope.showJobLog = function () {
        if (logIsOpen) return;
        var jobIndex = $scope.jobs.output.map(function (e) {
            return e.id;
        }).indexOf($scope.jobs.currentId);
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/runner/modals/log.html',
            size: 'lg',
            // windowClass: 'modal-window',
            resolve: {
                log: function () {
                    return $scope.jobs.output[jobIndex]
                }
            },
            controller: 'LogCtrl'
        });

        logIsOpen = true;

        modalInst.result.then(function () {
            logIsOpen = false;
        }, function () {
            logIsOpen = false;
        });
    };

    var codeIsOpen = false;
    $scope.showSourceCode = function () {
        if (codeIsOpen) return;
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/runner/modals/code.html',
            size: 'lg',
            resolve: {
                code: ['projectService', function(projectService){
                            return projectService.getModuleSourceCode($scope.module.filename);
                        }],
                language: function () {
                    return $scope.module.language;
                },
                name: function () {
                    return $scope.module.name;
                }
            },
            controller: 'CodeCtrl'
        });

        codeIsOpen = true;

        modalInst.result.then(function () {
            codeIsOpen = false;
        }, function () {
            codeIsOpen = false;
        });
    };

    $scope.goToNextJob = function () {
        console.log('jobs: ', $scope.jobs)
        var jobIndex = $scope.jobs.output.map(function (e) {
            return e.id;
        }).indexOf($scope.jobs.currentId);
        var nextJobIndex = jobIndex + 1;
        if (nextJobIndex >= 0 && $scope.jobs.output.length > nextJobIndex) {
            console.log('go to next job: ', $scope.jobs.output[nextJobIndex].id)
            $scope.jobs.currentId = $scope.jobs.output[nextJobIndex].id;
        }
    };

    $scope.goToPreviousJob = function () {
        var jobIndex = $scope.jobs.output.map(function (e) {
            return e.id;
        }).indexOf($scope.jobs.currentId);
        var previousJobIndex = jobIndex - 1;
        console.log('previous job index: ', previousJobIndex)
        if (previousJobIndex >= 0 && $scope.jobs.output.length > previousJobIndex) {
            console.log('go to previous job: ', $scope.jobs.output[previousJobIndex].id)
            $scope.jobs.currentId = $scope.jobs.output[previousJobIndex].id;
        }
    };

    var figureIsOpen = false;
    $scope.showFigure = function () {

        if (figureIsOpen) return;

        var modalInst = $uibModal.open({
            size: 'lg',
            templateUrl: 'src/jtui/components/runner/modals/figure.html',
            resolve: {
                figure: ['projectService', function(projectService){
                            return projectService.getModuleFigure(
                                    $stateParams.experimentid,
                                    $stateParams.projectName,
                                    $scope.module.name,
                                    $scope.jobs.currentId
                                );
                        }],
                name: function () {
                    return $scope.module.name;
                }
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
      combo: ['left', 'h'],
      description: 'go to previous job',
      callback: $scope.goToPreviousJob
    })
    .add({
      combo: ['right', 'l'],
      description: 'go to next job',
      callback: $scope.goToNextJob
    })
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
      description: 'show output (stdout/stderr) of current module and job',
      callback: $scope.showOutput
    })
    .add({
      combo: 'space',
      description: 'show log message of current job',
      callback: $scope.showJobLog
    })
    .add({
      combo: 'f',
      description: 'show figure of current module and job',
      callback: $scope.showFigure
    })

    $scope.showThumbnail = function () {
        if ($scope.jobs.currentId) {
            var jobIndex = $scope.jobs.output.map(function (e) {
                return e.id;
            }).indexOf($scope.jobs.currentId);
            for (i in $scope.jobs.output) {
                if (i == jobIndex) {
                    for (j in $scope.jobs.output[jobIndex].modules) {
                        if ($scope.jobs.output[jobIndex].modules[j].name == currentModuleName) {
                            var thumbnail = $scope.jobs.output[jobIndex].modules[j].thumbnail;
                            return thumbnail;
                        }
                    }
                }
            }
        }   
    };

    $scope.reportBug = function(){
        $window.open('https://github.com/TissueMAPS/JtLibrary/issues', '_blank');
    };

}]);
