class SetupCtrl {

    currentStage: WorkflowStage;
    workflow: Workflow;
    _monitoringPromise: ng.IPromise<void> = null;

    static $inject = ['experiment', 'plates', 'dialogService', '$state', '$interval', '$scope', '$uibModal'];

    isInStage(stage: WorkflowStage) {
        return this.currentStage.name === stage.name;
    }

    goToStage(stage: WorkflowStage) {
        this.currentStage = stage;
        // console.log('go to stage: ', this.currentStage)
        if (stage.name === 'upload') {
            this._$state.go('plate');
        } else {
            this._$state.go('setup.stage', {
                stageName: stage.name
            });
        }
    }

    private _isLastStage(stage: WorkflowStage): boolean {
        if (stage != undefined) {
            var idx = this.workflow.stages.indexOf(stage);
            return idx === this.workflow.stages.length - 1;
        } else {
            return false;
        }
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
        var idx = this.workflow.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                var desc = this.workflow.getDescription(idx);
                this._dialogService.warning('Do you really want to resume the workflow?')
                .then((resumeForReal) => {
                    if (resumeForReal) {
                        result = this._resubmitWorkflow(desc, idx - 1)
                        .then(function(res) {
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
        var desc = this.workflow.getDescription(this.workflow.stages.length - 1);
        // console.log('save workflow description: ', desc)
        this._saveWorkflowDescription(desc)
        .then((res) => {
            var result = {
                success: res.status == 200,
                message: res.statusText
            };
            this._displayResult('Save', result);
        });
    }

    submit() {
        var idx = this.workflow.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                var desc = this.workflow.getDescription(idx);
                this._dialogService.warning(
                    'Do you really want to submit the workflow?'
                )
                .then((submitForReal) => {
                    if (submitForReal) {
                        result = this._submitWorkflow(desc)
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
        var idx = this.workflow.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this.workflow.check(idx);
            var result;
            if (areStagesOk) {
                var desc = this.workflow.getDescription(idx);
                var stageNames = this.experiment.workflowDescription.stages.map((st) => {
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
                        for (var i = 0; i < this.experiment.workflowDescription.stages.length; i++) {
                            if (this.experiment.workflowDescription.stages[i].name == stageName) {
                                index = i;
                            }
                        }
                        result = this._resubmitWorkflow(desc, index)
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
        // var result = this.experiment.killWorkflow()
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
                            this._saveWorkflowDescription(desc)
                            this._getWorkflowDescription();
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
        if (this.currentStage == undefined) {
            return false;
        }
        if (this.currentStage.status == undefined) {
            return false;
        }
        else if (this.currentStage.status.state == 'RUNNING') {
            return false;
        } else {
            return true;
        }
    }

    canSubmit(): boolean {
        if (this.workflow == undefined) {
            return false;
        }
        if (this.workflow.status == undefined) {
            return false;
        } else {
            var blockedStates = [
                'RUNNING', 'NEW', 'TERMINATING', 'STOPPING', 'UNKNOWN'
            ];
            if (this.currentStage.name === 'upload') {
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
        var idx = this.workflow.stages.indexOf(this.currentStage);
        if (idx >= 0) {
            var inLastStage = idx == this.workflow.stages.length - 1;
            if (!inLastStage) {
                var newStage = this.workflow.stages[idx + 1];
                this.currentStage = newStage;
                this._$state.go('setup.stage', {
                    stageName: newStage.name
                }, {
                    reload: 'setup.stage'
                });
            }
        } else {
            throw new Error(
                'Cannot proceed to next stage from unknown stage ' + this.currentStage
            );
        }
    }

    update() {
        this._getWorkflowDescription()
    }

    getStatus() {
        console.log('get workflow status')
        this._getWorkflowStatus()
        .then((workflowStatus) => {
            // recursively update the job tree
            this.workflow.status = new JobCollectionStatus(workflowStatus);
            this.workflow.stages.map((stage, stageIndex) => {
                if (stageIndex == 0 && stage.name == 'upload') {
                    // hack around "upload" stage
                    stage.status = this._getUploadStatus();
                } else {
                    console.log('update stage: ', stage.name)
                    var workflowStageDescription = this.experiment.workflowDescription.stages[stageIndex - 1];
                    var workflowStageStatus = null;
                    if (stageIndex - 1 < workflowStatus.subtasks.length) {
                        var workflowStageStatus = workflowStatus.subtasks[stageIndex - 1];
                        stage.status = new JobCollectionStatus(workflowStageStatus);
                    }
                    // NOTE: The list of jobs within a step is subject to change,
                    // since steps are build dynamically upon processing.
                    // Therefore, we recreate the whole step, rather than just
                    // updating its status.
                    stage.steps.map((step, stepIndex) => {
                        if (workflowStageStatus != null) {
                            console.log('update step: ', step.name)
                            var workflowStepDescription = workflowStageDescription.steps[stepIndex];
                            var workflowStepStatus = workflowStageStatus.subtasks[stepIndex];
                            step = new WorkflowStep(
                                workflowStepDescription, workflowStepStatus
                            );
                            // TODO: how to access currentStep of stageCtrl??
                            // this._$scope.stageCtrl.currentStep = step;
                        }
                    });
                    if (stage.name === this.currentStage.name) {
                        // TODO: can't this be watched on scope?
                        this._$scope.setupCtrl.currentStage = stage;
                        this.currentStage = stage;
                    }
                }
            });
        });
    }

    private _getUploadStatus() {
        // TODO: this could be done server side based on the database entries
        // and included in the workflow status
        var uploadFailed = false;
        var processingState = '';
        var uploadStates = [];
        var uploadProgress = 0;
        var doneCount = 0;
        var totalCount = 0;
        this.plates.map((plt) => {
            plt.acquisitions.map((acq) => {
                totalCount++;
                uploadStates.push(acq.status);
                if (acq.status == 'FAILED') {
                    uploadFailed = true;
                    doneCount++;
                } else if (acq.status == 'COMPLETE') {
                    doneCount++;
                }
            });
        });
        uploadProgress = doneCount / totalCount * 100;
        if (uploadStates.every((s) => {return s == 'COMPLETE';})) {
            processingState = 'TERMINATED';
        } else if (uploadStates.some((s) => {return s == 'UPLOADING';})) {
            processingState = 'RUNNING';
        } else {
            processingState = 'NEW';
        }
        return new JobCollectionStatus({
            failed: uploadFailed,
            state: processingState,
            percent_done: uploadProgress,
            done: uploadProgress == 100,
            subtasks: [],  // TODO: monitor each acquisition individually
            name: 'fileupload',
            live: uploadProgress < 100,
            memory: null,
            type: null,
            exitcode: null,
            id: null,
            submission_id: null,
            time: null,
            cpu_time: null
        });

    }
    // starts the interval
    private _startMonitoring() {
        // stops any running interval to avoid two intervals running at the same time
        this._stopMonitoring();
        this.getStatus();
        // console.log('start monitoring status')
        this._monitoringPromise = this._$interval(() => {
                this.getStatus()
            }, 5000
        );
    }

    private _stopMonitoring() {
        // console.log('stop monitoring status')
        this._$interval.cancel(this._monitoringPromise);
        this._monitoringPromise = null;
    }

    // private _submitStages(stages: WorkflowStage[], redo: boolean, index: number) {
    //     // Only send the description up to the stage that the user submitted
    //     var desc = $.extend(true, {}, this.experiment.workflowDescription);
    //     desc.stages = [];
    //     stages.forEach((stage) => {
    //         desc.stages.push(stage);
    //     });
    //     if (redo) {
    //         this._resubmitWorkflow(desc, index);
    //     } else {
    //         this._submitWorkflow(desc);
    //     }
    // }

    private _submitWorkflow(workflowArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var data = {
            description: workflowArgs
        };
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/submit', data)
        .then((resp) => {
            // console.log(resp);
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return $q.reject(resp.data.error);
        });
    }

    private _createJteratorProject(projectName, templateName) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var data = {
            pipeline: projectName,
            template: templateName
        };
        return $http.post('/jtui/create_jtproject/' + this.experiment.id, data)
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
        var data = {
            pipeline: projectName
        };
        return $http.post('/jtui/remove_jtproject/' + this.experiment.id, data)
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

    private _resubmitWorkflow(workflowArgs, index) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var data = {
            description: workflowArgs,
            index: index
        };
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/resubmit', data)
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

    private _killWorkflow() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/kill', {})
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

    private _saveWorkflowDescription(workflowArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var data = {
            description: workflowArgs
        };
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/save', data)
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

    private _getWorkflowDescription(): ng.IPromise<any> {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.get('/api/experiments/' + this.experiment.id + '/workflow/load')
        .then((resp: any) => {
            // console.log(resp)
            this.experiment.workflowDescription = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return $q.reject(resp.data.error);
        });
    }

    private _getWorkflowStatus(): ng.IPromise<any> {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.get('/api/experiments/' + this.experiment.id + '/workflow/status')
        .then((resp: any) => {
            // console.log(resp)
            this.experiment.workflowStatus = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return $q.reject(resp.data.error);
        });
    }

    constructor(public experiment: Experiment,
                public plates: Plate[],
                private _dialogService: DialogService,
                private _$state,
                private _$interval,
                private _$scope,
                private _$uibModal: ng.ui.bootstrap.IModalService) {
        this._$scope.$watch('currentStage');
        this._getWorkflowDescription();
        this._getWorkflowStatus()
        .then((workflowStatus) => {
            // console.log(workflowStatus)
            // TODO: handle null status
            this.workflow = new Workflow(
                this.experiment.workflowDescription, workflowStatus
            );
            this.goToStage(this.workflow.stages[0]);
            //  start monitoring as soon as the user enters the "setup" view
            this._startMonitoring();
        });

        this._$scope.$on('$destroy', () => {
            // stop monitoring when user leaves the "setup" view
            this._stopMonitoring();
        });

    }
}

angular.module('tmaps.ui').controller('SetupCtrl', SetupCtrl);
