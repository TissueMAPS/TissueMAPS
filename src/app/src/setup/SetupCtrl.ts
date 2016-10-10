class SetupCtrl {

    currentStageIndex: number;
    _monitoringPromise: ng.IPromise<void> = null;

    static $inject = ['experiment', 'plates', 'workflow', 'workflowService', 'dialogService', '$state', '$interval', '$scope', '$uibModal'];

    isInStage(stage: WorkflowStage) {
        if (stage == undefined) {
            return false;
        }
        var idx = this.currentStageIndex;
        return this.workflow.stages[idx].name === stage.name;
    }

    goToStage(stage: WorkflowStage) {
        // console.log('go to stage: ', stage)
        if (!this.uploadComplete() && stage.name != 'upload') {
            this._dialogService.error(
                'Processing not yet possible! ' +
                'Upload incomplete or not yet fully loaded.'
            )
            this._$state.go('plate', {
                stageName: 'upload'
            });
        } else {
            this.currentStageIndex = this.workflow.stages.indexOf(stage);
            if (stage.name === 'upload') {
                this._$state.go('plate', {
                    stageName: stage.name
                });
            } else {
                var stepName = this._$state.params.stepName;
                if (stepName) {
                    this._$state.go('setup.step', {
                        stageName: stage.name,
                        stepName: stepName
                    });
                } else {
                    var stageIdx = this.currentStageIndex;
                    stepName = this.workflow.stages[stageIdx].steps[0].name;
                    this._$state.go('setup.step', {
                        stageName: stage.name,
                        stepName: stepName
                });
                }
            }
        }
    }


    private _isLastStage(stage: WorkflowStage): boolean {
        if (stage == undefined) {
            return false;
        }
        var idx = this.currentStageIndex;
        return idx === this.workflow.stages.length - 1;
    }

    uploadComplete() {
        return this.plates.every((plate) => {
            return this.workflow.stages[0].status.state == 'TERMINATED';
        });
    }

    canProceedToNextStage(stage: WorkflowStage): boolean {
        if (stage == undefined) {
            return false;
        }
        if (this._isLastStage(stage)) {
            return false;
        } else {
            return stage.check();
        }
    }

    resume() {
        var idx = this.currentStageIndex;
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                this._dialogService.warning('Do you really want to resume the workflow?')
                .then((resumeForReal) => {
                    if (resumeForReal) {
                        var restartAt;
                        for (var i = 1; i < this.workflow.stages.length; i++) {
                            if (!this.workflow.stages[i].status.done) {
                                // account for first stage "upload"
                                restartAt = i - 1;
                                break;
                            }
                        }
                        result = this._workflowService.resubmit(
                            this.experiment, idx, restartAt
                        )
                        .then((res) => {
                            return {
                                success: res.status == 200,
                                message: res.statusText
                            }
                        });
                        this._displayResult('Resume', result);
                    }
                });
            } else {
                result = {
                    sucess: false,
                    message: 'Values for required arguments are missing'
                };
                this._displayResult('Resume', result);
            }
        }
    }

    save() {
        this._workflowService.save(this.experiment)
        .then((res) => {
            var result = {
                success: res.status == 200,
                message: res.statusText
            };
            this._displayResult('Save', result);
        });
    }

    submit() {
        var idx = this.currentStageIndex;
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                this._dialogService.warning(
                    'Do you really want to submit the workflow?'
                )
                .then((submitForReal) => {
                    if (submitForReal) {
                        result = this._workflowService.submit(
                            this.experiment, idx
                        )
                        .then((res) => {
                            return {
                                success: res.status == 200,
                                message: res.statusText
                            }
                        });
                        this._displayResult('Submit', result);
                    }
                });
            } else {
                result = {
                    sucess: false,
                    message: 'Values for required arguments are missing'
                };
                this._displayResult('Submit', result);
            }
        }
    }

    resubmit() {
        var idx = this.currentStageIndex;
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                var description = this.workflow.getDescription(idx);
                var stageNames = description.stages.map((st) => {
                    return st.name
                });
                this._getInput(
                    'Resubmit',
                    'Stage from which workflow should be resubmitted:',
                    'dropdown',
                    stageNames
                )
                .then((stageName) => {
                    // console.log('resubmit starting at stage: ', stageName)
                    var result;
                    if (stageName !== undefined) {
                        var index = 0;
                        for (var i = 0; i < description.stages.length; i++) {
                            if (description.stages[i].name == stageName) {
                                index = i;
                            }
                        }
                        result = this._workflowService.resubmit(
                            this.experiment, idx, index
                        )
                        .then((res) => {
                            return {
                                success: res.status == 200,
                                message: res.statusText
                            }
                        });
                        this._displayResult('Resubmit', result);
                    } else {
                        result = {
                            success: false,
                            message: 'No stage selected'
                        };
                        this._displayResult('Resubmit', result);
                    }
                });
            } else {
                result = {
                    sucess: false,
                    message: 'Values for required arguments are missing'
                };
                this._displayResult('Resubmit', result);
            }
        }

    }

    kill() {
        var result = {
            success: false,
            message: 'Not yet implemented'
        };
        // var result = this._workflowService.kill(this.experiment)
        // .then(function(res) {
        //     return {
        //         success: res.status == 200,
        //         message: res.statusText
        //     }
        // });
        this._displayResult('Kill', result);
    }

    deletePipeline(s: WorkflowStep) {
        var projectName = '';
        for (var arg in s.extra_args) {
            if (s.extra_args[arg].name == 'pipeline') {
                projectName = s.extra_args[arg].value;
            }
        }
        var result;
        if (projectName == '' || projectName == null) {
            result = {
                success: false,
                message: 'No pipeline selected.'
            };
            this._displayResult('Delete pipeline', result);
        } else {
            // console.log('pipeline that should be deleted: ', projectName)
            this._dialogService.warning(
                'Do you really want to delete the pipeline?'
            )
            .then((deleteForReal) => {
                if (deleteForReal) {
                    // console.log('delete pipeline HAAAAARD')
                    result = this._removeJteratorProject(projectName)
                    .then((res) => {
                        result = {
                            success: res.status == 200,
                            message: res.statusText
                        };
                        this._displayResult('Delete Pipeline', result);
                        if (result.success) {
                            // reload descrioption such that choices are
                            // updated
                            var desc = this.workflow.getDescription(
                                this.workflow.stages.length - 1
                            );
                            this._workflowService.save(this.experiment)
                            this._workflowService.update(
                                this.experiment, this.plates
                            );
                        }
                    });
                }
            });
        }
    }

    createPipeline() {
        // TODO: create template pipelines
        var pipelineNames = [];
        this._getInput(
            'Create pipeline',
            'Select a pipeline template:',
            'dropdown',
            pipelineNames
        )
        .then((templateName) => {
            if (templateName == undefined) {
                templateName = null;
            }
            // console.log('create new pipeline using template: ', templateName)
            this._getInput(
                'Create pipeline',
                'How should the new pipeline be called?',
                'text',
                null
            )
            .then((pipeName) => {
                // console.log('create pipeline: ', pipeName)
                this._createJteratorProject(pipeName, templateName)
                .then((res) => {
                    var result = {
                        success: res.status == 200,
                        message: res.statusText
                    };
                    if (result.success) {
                        this._$state.go('project', {
                            experimentid: this.experiment.id,
                            projectName: pipeName
                        });
                    } else {
                        this._displayResult('Create pipeline', result);
                    }
                });
            });
        });
    }

    editPipeline(s: WorkflowStep) {
        var project = '';
        for (var arg in s.extra_args) {
            if (s.extra_args[arg].name == 'pipeline') {
                project = s.extra_args[arg].value;
            }
        }
        // console.log(project)
        if (project == '' || project == null) {
            var result = {
                success: false,
                message: 'No pipeline selected.'
            };
            this._displayResult('Edit pipeline', result);
        } else {
            this._$state.go('project', {
                experimentid: this.experiment.id,
                projectName: project
            });
        }
    }

    private _getInput(task: string, description: string, widgetType: string, choices: any) {
        var options: ng.ui.bootstrap.IModalSettings = {
            templateUrl: 'src/setup/modals/input.html',
            controller: SetupInputCtrl,
            controllerAs: 'input',
            resolve: {
                title: () => task,
                message: () => description,
                widgetType: () => widgetType,
                choices: () => choices
            }
        };
        return this._$uibModal.open(options).result;
    }

    private _displayOutput(stdout: string, stderr: string) {
        var options: ng.ui.bootstrap.IModalSettings = {
            templateUrl: 'src/setup/modals/output.html',
            controller: SetupOutputCtrl,
            controllerAs: 'output',
            size: 'lg',
            resolve: {
                title: () => 'Log output',
                stdout: () => stdout,
                stderr: () => stderr
            }
        };
        return this._$uibModal.open(options).result;
    }

    private _displayResult(task: string, response: any) {
        var options: ng.ui.bootstrap.IModalSettings = {
            templateUrl: 'src/setup/modals/result.html',
            controller: SetupResultCtrl,
            controllerAs: 'result',
            resolve: {
                title: () => task,
                response: () => response
            }
        };
        return this._$uibModal.open(options).result;
    }

    canModifyPipeline(): boolean {
        var idx = this.currentStageIndex;
        if (this.workflow.stages[idx] == undefined) {
            return false;
        }
        if (this.workflow.stages[idx].status == undefined) {
            return false;
        }
        else if (this.workflow.stages[idx].status.state == 'RUNNING') {
            return false;
        } else {
            return true;
        }
    }

    canSubmit(): boolean {
        var idx = this.currentStageIndex;
        if (this.workflow == undefined) {
            return false;
        }
        if (this.workflow.status == undefined) {
            return false;
        } else {
            var blockedStates = [
                'RUNNING', 'NEW', 'TERMINATING', 'STOPPING', 'UNKNOWN'
            ];
            if (this.workflow.stages[idx].name === 'upload') {
                // Submit button should not be pressable from upload files stage
                return false;
            } else if (blockedStates.indexOf(this.workflow.status.state) != -1) {
                // workflowStatus should be prevented when the workflow is already
                // running or in any other state that would cause problems
                return false;
            } else {
                return true;
            }
        }
    }

    canResubmit(): boolean {
        if (this.workflow == undefined) {
            return false;
        }
        if (this.workflow.status == undefined) {
            return false;
        } else {
            var resubmittableStates = [
                'TERMINATED', 'STOPPED'
            ];
            return this.canSubmit() && resubmittableStates.indexOf(this.workflow.status.state) != -1;
        }
    }

    goToNextStage() {
        var idx = this.currentStageIndex;
        if (idx >= 0) {
            var inLastStage = idx == this.workflow.stages.length - 1;
            if (!inLastStage) {
                var newStage = this.workflow.stages[idx + 1];
                this.currentStageIndex = this.workflow.stages.indexOf(newStage);
                this._$state.go('setup.stage', {
                    stageName: newStage.name
                }, {
                    reload: 'setup.stage'
                });
            }
        } else {
            throw new Error(
                'Cannot proceed to next stage from unknown stage '
            );
        }
    }

    update() {
        this._workflowService.getWorkflow(this.experiment);
    }

    getStatus() {
        this._workflowService.update(this.experiment, this.plates);
    }

    getLogOutput(job: Job) {
        console.log('get log output')
        this._workflowService.getLogOutput(this.experiment, job.dbId)
        .then((res) => {
            var result = {
                success: res.status == 200,
                message: res.statusText
            };
            if (result.success) {
                var log = res.data;
                this._displayOutput(log.stdout, log.stderr);
            } else {
                this._displayResult('Log', result);
            }
        })
    }

    private _startMonitoring() {
        // stops any running interval to avoid two intervals running at the same time
        this._stopMonitoring();
        this.getStatus();
        // console.log('start monitoring status')
        this._monitoringPromise = this._$interval(() => {
                this.getStatus()
            }, 10000
        );
    }
    private _stopMonitoring() {
        // console.log('stop monitoring status')
        this._$interval.cancel(this._monitoringPromise);
        this._monitoringPromise = null;
    }

    private _createJteratorProject(projectName, templateName) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var url = '/jtui/experiments/' + this.experiment.id +
                  '/projects/' + projectName + '/create';
        return $http.post(url, {'template': templateName})
        .then((resp) => {
            // console.log(resp)
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return $q.reject(resp.data.error);
        });
    }

    private _removeJteratorProject(projectName) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var url = '/jtui/experiments/' + this.experiment.id +
                  '/projects/' + projectName + '/delete';
        return $http.post(url, {})
        .then((resp) => {
            // console.log(resp)
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return $q.reject(resp.data.error);
        });
    }

    constructor(public experiment: Experiment,
                public plates: Plate[],
                public workflow: Workflow,
                private _workflowService: WorkflowService,
                private _dialogService: DialogService,
                private _$state,
                private _$interval,
                private _$scope,
                private _$uibModal: ng.ui.bootstrap.IModalService) {
        // console.log(this.workflow)
        // We need to keep up to date with chages of the workflow status
        // (including the status of plates for the "upload" stage)
        this.workflow = this._workflowService.workflow;
        this.plates = plates;
        var stageName = this._$state.params.stageName;
        this.workflow.stages.map((stage, stageIndex) => {
            if (stage.name == stageName) {
                this.currentStageIndex  = stageIndex;
            }
        })

        this.goToStage(this.workflow.stages[this.currentStageIndex]);
        //  start monitoring as soon as the user enters the "setup" view
        this._startMonitoring();
        // stop monitoring when the scope gets destroyed, i.e. when the user
        // leaves the "setup" view
        this._$scope.$on('$destroy', () => {
            this._stopMonitoring();
        });

    }
}

angular.module('tmaps.ui').controller('SetupCtrl', SetupCtrl);
