angular.module('jtui.project')
.controller('ProjectCtrl', ['$scope', '$state', '$stateParams', '$interval', 'project', 'channels', 'projectService', 'runnerService', '$uibModal', 'hotkeys',
            function ($scope, $state, $stateParams, $interval, project, channels, projectService, runnerService, $uibModal, hotkeys) {

    console.log('project: ', project)
    $scope.project = project;

    console.log('channels: ', channels)
    $scope.channels = channels;

    $scope.project.viewProps = {
        selected: true,
        open: {
            project: false,
            jobs: false,
            pipeline: true
        }
    };

    $scope.processing = false;

    var checkIsOpen = false;
    $scope.checkProject = function() {
        if (checkIsOpen) return;
        console.log('check project:', $scope.project)
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/check.html',
            size: 'sm',
            resolve: {
                checked: ['projectService', function(projectService){
                            return projectService.checkProject($scope.project);
                }]
            },
            controller: 'CheckCtrl'
        });

        checkIsOpen = true;

        modalInst.result.then(function () {
            checkIsOpen = false;
        }, function () {
            checkIsOpen = false;
        });
    }

    var saveIsOpen = false;
    $scope.saveProject = function() {
        if (saveIsOpen) return;
        console.log('save project:', $scope.project)
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/save.html',
            size: 'sm',
            resolve: {
                saved: ['projectService', function(projectService){
                            return projectService.saveProject($scope.project);
                }]
            },
            controller: 'SaveCtrl'
        });

        saveIsOpen = true;

        modalInst.result.then(function () {
            saveIsOpen = false;
        }, function () {
            saveIsOpen = false;
        });
    }

    var runIsOpen = false;
    $scope.run = function(project) {
        if (runIsOpen) return;
        console.log('run project:', $scope.project);
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/run.html',
            controller: 'RunCtrl'
        });

        runIsOpen = true;

        modalInst.result.then(function () {

            console.log('job ids:', $scope.subJobId.map(Number))
            if ($scope.subJobId.length > 10) {
                console.log('too many jobs');
                return
            }
            if ($scope.subJobId != null) {
                var check = false;
                // First save the pipeline and return potential errors
                projectService.saveProject($scope.project).then(function (result) {
                    console.log('save result: ', result);
                    if (!result.success) {
                        console.log('pipeline could not be saved');
                        // Show the error
                        $scope.saveProject();
                    } else {
                        // Then check the pipeline and return potential errors
                        projectService.checkProject($scope.project).then(function (result) {
                            console.log('check result: ', result);
                            if (!result.success) {
                                console.log('pipeline check failed');
                                // Show the error
                                $scope.checkProject();
                            } else {
                                console.log('pipeline check successful');
                                // Submit pipeline for processing
                                console.log('submit pipeline');
                                runnerService.run($scope.subJobId, $scope.project);
                                console.log('---START MONITORING SUBMISSION STATUS---')
                                $scope.startMonitoring();
                        }
                        });

                    }
                });
            }
            runIsOpen = false;
        }, function () {
            runIsOpen = false;
        });
    }

    var killIsOpen = false;
    $scope.kill = function() {
        if (killIsOpen) return;
        console.log('kill jobs: ', $scope.taskId)
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/kill.html',
            size: 'sm',
            resolve: {
                killed: ['runnerService', function(runnerService){
                    return runnerService.kill($scope.project, $scope.taskId);
                }]
            },
            controller: 'KillCtrl'
        });

        killIsOpen = true;

        modalInst.result.then(function () {
            killIsOpen = false;
        }, function () {
            killIsOpen = false;
        });
    }

    var listIsOpen = false;
    $scope.listJobs = function() {
        if (listIsOpen) return;
        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/joblist.html',
            size: 'lg',
            resolve: {
                joblist: ['projectService', function(projectService){
                    return projectService.createJoblist($scope.project).then(function (data) {
                        console.log(data.joblist)
                        return data.joblist;
                    });
                }]
            },
            controller: 'JoblistCtrl'
        });

        listIsOpen = true;

        modalInst.result.then(function () {
            listIsOpen = false;
        }, function () {
            listIsOpen = false;
        });
    }

    // Define keyboard shortcuts
    hotkeys.bindTo($scope)
    .add({
      combo: 'c',
      description: 'check pipeline',
      callback: $scope.checkProject
    })
    .add({
      combo: 's',
      description: 'save pipeline',
      callback: $scope.saveProject
    })
    .add({
      combo: 'r',
      description: 'run pipeline',
      callback: $scope.run
    })
    .add({
      combo: 'k',
      description: 'kill submitted jobs',
      callback: $scope.kill
    })
    .add({
      combo: 'j',
      description: 'list jobs',
      callback: $scope.listJobs
    })
    
    $scope.getSelectableChannelNames = function(index) {
        selectableImageNames = [];
        selectedImageNames = [];
        for (var i in $scope.project.pipe.description.input.channels) {
            if (i != index) {
                selectedImageNames.push($scope.project.pipe.description.input.channels[i].name);
            }
        }
        for (var i in $scope.channels) {
            if (selectedImageNames.indexOf($scope.channels[i]) == -1) {
                selectableImageNames.push($scope.channels[i]);
            }
        }
        return selectableImageNames;
    };

    // Initialize empty array for selection of modules
    $scope.selectedModules = [];

    $scope.getModuleName = function(ixPipe) {
        // Necessary to be up-to-date with module name
        // TODO: consider $watch()
        return($scope.project.pipe.description.pipeline[ixPipe].name);
    };

    $scope.isShiftSelected = function(module_name) {
        var ixSelected = $scope.selectedModules.indexOf(module_name);
        if (ixSelected > -1) {
            return true
        } else {
            false
        }
    };

    function getStatus() {
        runnerService.getStatus($scope.project).then(function (result) {
            console.log('status: ', result.status)
            if (result.status == null) {
                $scope.outputAvailable = false;
            } else {
                $scope.outputAvailable = true;
                $scope.submission.state = result.status.state;
                $scope.submission.progress = result.status.percent_done;
                if (result.status.failed) {
                    $scope.submission.indicator = 'danger';
                } else {
                    $scope.submission.indicator = 'success';
                }
                if (result.status.is_done) {
                    console.log('---STOP MONITORING SUBMISSION STATUS---')
                    $scope.stopMonitoring();
                    getOutput();
                }
            }
        });
    };

    function getOutput() {
        runnerService.getOutput($scope.project).then(function (result) {
            console.log('output: ', result.output)
            if (result.output) {
                result.output.forEach(function(r) {
                    $scope.jobs.output.push(r);
                });
                $scope.jobs.currentId = result.output[0].id;
                $scope.$watch('jobs.currentId');
                $scope.outputAvailable = true;
                var unkown = $scope.jobs.output.every(function (element, index, array) {
                    return element.failed === null;
                });
                var failed = $scope.jobs.output.some(function (element, index, array) {
                    return element.failed;
                });
                if (unkown) {
                    $scope.type = '';
                } else if (failed) {
                    $scope.submission.indicator = 'danger';
                } else {
                    $scope.submission.indicator = 'success';
                }
            }
        });
    };

    // One needs to provide default values to keep the progressbar at zero
    $scope.submission = {
        progress: 0,
        state: "",
        indicator: 'success'
    };
    $scope.type = "";

    // starts the interval
    var promise;
    $scope.startMonitoring = function() {
        // stops any running interval to avoid two intervals running at the same time
        $scope.stopMonitoring();
        promise = $interval(getStatus, 5000);
    };

    $scope.stopMonitoring = function() {
        $interval.cancel(promise);
    };

    $scope.$on('$destroy', function() {
        $scope.stopMonitoring();
    });

    // runnerService.socket.$on('status', function (data) {
    //     console.log('status received from server: ', data);
    //     if ($state.is('project')) {
    //         $state.go('project.module', {
    //         moduleName: $scope.project.handles[0].name
    //     });
    //     }
    //     $scope.taskId = data.id;
    //     $scope.state = data.state;
    //     $scope.isDone = data.subtasks[0].is_done;
    //     $scope.progress = data.subtasks[0].percent_done;

    //     if (data.subtasks[0].failed) {
    //         $scope.type = 'danger';
    //     }
    //     else {
    //         $scope.type = 'success';
    //     }
    //     $scope.$apply();
    // });

    $scope.jobs = {
        output: [],
        currentId: null
    };
    $scope.outputAvailable = false;
    // Start monitoring in case the website got disconnected.
    // This should automatically stop, once the jobs are TERMINATED
    $scope.startMonitoring();
    // Get the output of all jobs
    getOutput();

    // runnerService.socket.$on('output', function (data) {

    //     console.log('output received from server: ', data);
    //     $scope.jobs.output = data;

    //     if ($scope.subJobId) {
    //         $scope.jobs.currentId = parseInt($scope.subJobId[0]);
    //     }
    //     $scope.$apply();
    //     $scope.outputAvailable = true;
    // });

    $scope.activateModule = function(index, $event) {
        if ($event.shiftKey) {
            console.log('click ignored')
        } else {
            $scope.project.pipe.description.pipeline[index].active = true;
            var mod = $scope.project.pipe.description.pipeline[index].name;
            console.log('activate module: ', mod)
        }
    }

    $scope.deactivateModule = function(index, $event) {
        if ($event.shiftKey) {
            console.log('click ignored')
        } else {
            $scope.project.pipe.description.pipeline[index].active = false;
            var mod = $scope.project.pipe.description.pipeline[index].name;
            console.log('deactivate module: ', mod)
        }
    }

    $scope.storeModuleName = function(oldModuleName, newModuleName) {
        console.log('old module name in pipe: ', oldModuleName)
        $scope.oldModuleName = oldModuleName;
        console.log('new module name: ', newModuleName)
        var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                return e.name;
            }).indexOf(newModuleName);
        // Module names must be unique!
        if (ixPipe == -1) {
            // Allow editing
            return true;
        } else {
         // Prevent editing
            // TODO: show message!
            return false;
        }
    }

    $scope.removeModule = function(module, $parent, $event) {
        if ($event.shiftKey) {
            console.log('click ignored')
        } else {
            var mod = module.name;
            console.log(mod)
            var ixHandles = $scope.project.handles.map(function(e) { 
                    return e.name;
                }).indexOf(mod);
            var ixPipe = $scope.project.pipe.description.pipeline.map(function(e) { 
                    return e.name;
                }).indexOf(mod);
            var ixAdded = $scope.addedModuleNames.indexOf(mod)
            if (ixHandles > -1) {
                var currentProject = $scope.project
                console.log('remove module \"' + mod + '\"');
                currentProject.handles.splice(ixHandles, 1);
                currentProject.pipe.description.pipeline.splice(ixPipe, 1)
                // Also remove from the list of selected modules
                ixSelected = $scope.selectedModules.indexOf(mod.name);
                $scope.selectedModules.splice(ixSelected, 1);
                $scope.addedModuleNames.splice(ixAdded, 1)
                console.log('update project:', currentProject)
                $scope.project = currentProject;
                // TODO: if currently displayed module is removed, go pack to
                // parent state (i.e. change url and view) 
                if ($parent.selected == module) {
                    console.log('go back to parent state')
                    $state.go('^');
                }
            } else {
                console.log('removal of module \"' + mod + '\" failed');
            }
        }
    }

    $scope.editModuleName = function(ixPipe, newModuleName) {
        console.log('new module name in pipe: ', newModuleName)
        var oldModuleName = $scope.oldModuleName;
        // We have to edit the related descriptions as well
        console.log('rename corresponding handles description')
        $scope.oldModuleName = [];
        var ixHandles = $scope.project.handles.map(function(e) { 
                return e.name;
            }).indexOf(oldModuleName);
        $scope.project.handles[ixHandles].name = newModuleName;
        console.log('rename handles in pipeline description')
        var oldHandlesFile = $scope.project.pipe.description.pipeline[ixPipe].handles
        var newHandlesFile = oldHandlesFile.replace(oldModuleName, newModuleName);
        console.log('handles file: ', newHandlesFile)
        $scope.project.pipe.description.pipeline[ixPipe].handles = newHandlesFile;
        $scope.project.pipe.description.pipeline[ixPipe].name = newModuleName;
        ixSelected = $scope.selectedModules.indexOf(oldModuleName);
        $scope.selectedModules[ixSelected] = newModuleName;
    };

    $scope.showLayersInTmaps = function () {
        console.log('not yet implemented')
    };

    $scope.addChannel = function() {
        var newChannel = {
            name: '',
            correct: true
        };
        $scope.project.pipe.description.input.channels.push(newChannel);
        console.log('added new channel')
    };

    $scope.removeChannel = function() {
        // Remove last pattern in list
        $scope.project.pipe.description.input.channels.pop();
        console.log('removed last channel')
    };

    $scope.addedModuleNames = [];

    $scope.onDropCompleteAdd = function(addedModule, evt) {
        if (addedModule != null) {
            var ixHandles = $scope.project.handles.map(function(e) { 
                    return e.name;
                }).indexOf(addedModule.name);
            if (ixHandles == -1) {
                console.log('add module \"' + addedModule.name + '\"')
                // If module doesn't yet exist in pipeline simply add it
                var newName = addedModule.name;

            } else {
                console.log('\"' + addedModule.name + '\" already exists. Rename it.')
                // If a module with the same name already exists in the pipeline rename
                // the newly added module to assert that each handles filename is unique
                var re = new RegExp(addedModule.name + '_(\\d+)$', 'i');
                var exists = function(element) {
                    return /.*_\d+$/.test(element);
                };
                if ($scope.addedModuleNames.some(exists)) {
                    var previousNumbers = [];
                    for (var i in $scope.addedModuleNames) {
                        var e = $scope.addedModuleNames[i];
                        if (e.match(re)) {
                            previousNumbers.push(parseInt(e.match(re)[1]));
                        }
                    }
                    console.log('previous numbers: ', previousNumbers)
                    if (previousNumbers.length > 0) {
                        var newNumber = Math.max.apply(Math, previousNumbers) + 1;
                        var newName = addedModule.name + '_' + newNumber.toString();
                    } else {
                        var newName = addedModule.name + '_1';
                    }
                } else {
                    var newName = addedModule.name + '_1';
                }
            }
            $scope.addedModuleNames.push(newName);

            // The "Module" object contains both, 'handles' description and
            // 'pipe' description. Update the project accordingly.
            // NOTE: the description has to be copied, otherwise the
            // $$hashKey element won't be updated, which would screw up the
            // ng-repeat directive
            var newHandlesObject = {
                        name: newName,
                        description: angular.copy(addedModule.description)
            };
            console.log('handles object of added module:', newHandlesObject)
            $scope.project.handles.push(newHandlesObject);
            var defaultName = addedModule.pipeline.handles;
            var newHandlesFilename = defaultName.replace(addedModule.name, newName);
            var newDescription = {
                        name: newName,
                        handles: newHandlesFilename,
                        source: addedModule.pipeline.source,
                        active: addedModule.pipeline.active
            };
            console.log('pipeline description of added module:', newDescription)
            $scope.project.pipe.description.pipeline.push(newDescription);
            $scope.$apply();
        }
    }


    $scope.getHelpForPipeline = function() {
        console.log('get help for pipeline')

        var modalInst = $uibModal.open({
            templateUrl: 'src/jtui/components/project/modals/pipeHelp.html',
            controller: 'PipeHelpCtrl'
        });

        modalInst.result.then(function() {});

    }

}]);

