interface Stage {
    name: string;
    steps: any[];
    active: boolean;
    mode: string;
}

class SetupCtrl {

    currentStage: Stage;
    currentStageSubmission: any;
    stages: Stage[];
    submission: any;
    _monitoringPromise: ng.IPromise<void> = null;

    static $inject = ['experiment', 'plates', '$state', '$interval', '$scope', '$uibModal'];

    isInStage(stage: Stage) {
        return this.currentStage.name === stage.name;
    }

    goToStage(stage: Stage) {
        this.currentStage = stage;
        if (stage.name === 'uploadfiles') {
            this._$state.go('plate');
        } else {
            this._$state.go('setup.stage', {
                stageName: stage.name
            });
        }
    }

    private _updateWorkflowDescription(index: number) {
        var desc = $.extend(true, {}, this.experiment.workflowDescription);
        desc.stages = [];
        for (var i = 1; i < this.stages.length;  i++) {
            // The 1. stage "uploadfiles" is not a stages that can
            // be submitted. It will be removed from the description.
            if (index < i) {
            // if (index < i && i < this.stages.length) {
                // These stages should not be submitted. They will
                // be included in the description, but set inactive.
                this.stages[i].active = false;
            } else {
                // in case they have been inactivated previously for whatever
                // reason
                this.stages[i].active = true;
            }
            desc.stages.push(this.stages[i]);
        }
        return desc;
    }

    private _checkArgsForWorkflowStage(stage: Stage): boolean {
        var submissionArgsAreValid, batchArgsAreValid, extraArgsAreValid;
        var isValid: boolean;

        function checkArgs(args) {
            return _.chain(args).map((arg) => {
                var isValid;
                if (arg.required) {
                    isValid = arg.value !== undefined
                        && arg.value !== null
                        && arg.value !== '';
                } else {
                    isValid = true;
                }
                return isValid;
            }).all().value();
        }

        var areStepsOk: boolean[] =  stage.steps.map((step) => {
            batchArgsAreValid = checkArgs(step.batch_args);
            submissionArgsAreValid = checkArgs(step.submission_args);

            if (step.extra_args) {
                extraArgsAreValid = checkArgs(step.extra_args);
            } else {
                extraArgsAreValid = true;
            }

            return batchArgsAreValid && submissionArgsAreValid && extraArgsAreValid;
        });
        return _.all(areStepsOk);
    }

    private _isUploadStageOk() {
        var atLeastOnePlate = this.plates.length > 0;
        var allPlatesReady = _.all(this.plates.map((pl) => {
            return pl.isReadyForProcessing;
        }));
        var isUploadStageOk = atLeastOnePlate && allPlatesReady;
        return isUploadStageOk;
    }

    private _areWorkflowStagesOk(index: number) {
        return _.all(this.stages.map((st, idx) => {
            if (idx == 0) {
                // first stage "uploadfiles" is not checked here
                return true;
            } else if (idx <= index) {
                return this._checkArgsForWorkflowStage(st);
            } else {
                // subsequent step which don't get submitted
                // are not checked here
                return true;
            }
        }));
    }

    private _areAllStagesOk(): boolean {
        var index = this.experiment.workflowDescription.stages.length - 1;
        return this._isUploadStageOk() && this._areWorkflowStagesOk(index);
    }

    private _isLastStage(stage): boolean {
        var idx = this.stages.indexOf(stage);
        return idx === this.stages.length - 1;
    }

    canProceedToNextStage(): boolean {
        if (this._isLastStage(this.currentStage)) {
            return false;
        } else if (this.currentStage.name === 'uploadfiles') {
            return this._isUploadStageOk();
        } else {
            return this._checkArgsForWorkflowStage(this.currentStage);
        }
    }

    resume() {
        var idx = this.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this._areWorkflowStagesOk(idx);
            var result;
            if (areStagesOk) {
                var desc = this._updateWorkflowDescription(idx);
                this._getFeedback(
                    'Resume',
                    'Do you really want to resume the workflow?'
                )
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
        var desc = this._updateWorkflowDescription(this.stages.length - 1);
        console.log('save workflow description: ', desc)
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
        var idx = this.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this._areWorkflowStagesOk(idx);
            var result;
            if (areStagesOk) {
                var desc = this._updateWorkflowDescription(idx);
                this._getFeedback(
                    'Submit',
                    'Do you really want to submit the workflow?'
                )
                .then((submitForReal) => {
                    if (submitForReal) {
                        result = this._submitWorkflow(desc)
                        .then(function(res) {
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
        var idx = this.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var areStagesOk = this._areWorkflowStagesOk(idx);
            var result;
            if (areStagesOk) {
                var desc = this._updateWorkflowDescription(idx);
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
                    console.log('resubmit starting at stage: ', stageName)
                    var result;
                    if (stageName !== undefined) {
                        var index = 0;
                        for (var i = 0; i < this.experiment.workflowDescription.stages.length; i++) {
                            if (this.experiment.workflowDescription.stages[i].name == stageName) {
                                index = i;
                            }
                        }
                        result = this._resubmitWorkflow(desc, index)
                        .then(function(res) {
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

    deletePipeline(s: Step) {
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
            console.log('pipeline that should be deleted: ', projectName)
            this._getFeedback(
                'Delete pipeline',
                'Do you really want to delete the pipeline?'
            )
            .then((deleteForReal) => {
                if (deleteForReal) {
                    console.log('delete pipeline HAAAAARD')
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
                            var desc = this._updateWorkflowDescription(
                                this.stages.length - 1
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
            console.log('create new pipeline using template: ', templateName)
            this._getInput(
                'Create pipeline',
                'How should the new pipeline be called?',
                'text',
                null
            )
            .then((pipeName) => {
                console.log('create pipeline: ', pipeName)
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

    editPipeline(s: Step) {
        var project = '';
        for (var arg in s.extra_args) {
            if (s.extra_args[arg].name == 'pipeline') {
                project = s.extra_args[arg].value;
            }
        }
        console.log(project)
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

    private _getFeedback(task: string, description: string) {
        var options: ng.ui.bootstrap.IModalSettings = {
            templateUrl: 'src/dialog/dialog.html',
            controller: DialogCtrl,
            controllerAs: 'dialog',
            resolve: {
                title: () => task,
                message: () => description,
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
        if (this.currentStageSubmission == undefined) {
            return false;
        }
        else if (this.currentStageSubmission.state == 'RUNNING') {
            return false;
        } else {
            return true;
        }
    }

    canSubmit(): boolean {
        var blockedStates = [
            'RUNNING', 'NEW', 'TERMINATING', 'STOPPING', 'UNKNOWN'
        ];
        if (this.currentStage.name === 'uploadfiles') {
            // Submit button should not be pressable from upload files stage
            return false;
        } else if (blockedStates.indexOf(this.submission.state) != -1) {
            // Submission should be prevented when the workflow is already
            // running or in any other state that would cause problems
            return false;
        } else {
            return true;
        }
    }

    canResubmit(): boolean {
        var resubmittableStates = [
            'TERMINATED', 'STOPPED'
        ];
        return this.canSubmit() && resubmittableStates.indexOf(this.submission.state) != -1;
    }

    isRunning(): boolean {
        if (this.submission.state == 'RUNNING') {
            return true;
        } else {
            return false;
        }
    }

    goToNextStage() {
        var idx = this.stages.indexOf(this.currentStage);
        if (idx >= 0) {
            var inLastStage = idx == this.stages.length - 1;
            if (!inLastStage) {
                var newStage = this.stages[idx + 1];
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
        this._getWorkflowStatus();
        this.submission = this.experiment.workflowStatus;
        if (this.submission == null) {
            this.submission = {
                is_done: false,
                failed: false,
                percent_done: 0,
                state: ''
            };
            this.currentStageSubmission = {
                is_done: false,
                failed: false,
                percent_done: 0,
                state: ''
            }
        } else {
            var idx = this.stages.indexOf(this.currentStage) - 1;
            if (idx >= this.submission.subtasks.length) {
                this.currentStageSubmission = {
                    is_done: false,
                    failed: false,
                    percent_done: 0,
                    state: ''
                };
            } else {
                this.currentStageSubmission = this.submission.subtasks[idx];
            }
        }
    }

    // starts the interval
    private _startMonitoring() {
        // stops any running interval to avoid two intervals running at the same time
        this._stopMonitoring();
        this.getStatus();
        console.log('start monitoring status')
        this._monitoringPromise = this._$interval(() => {
                this.getStatus()
            }, 5000
        );
    }

    private _stopMonitoring() {
        console.log('stop monitoring status')
        this._$interval.cancel(this._monitoringPromise);
        this._monitoringPromise = null;
    }

    private _submitStages(stages: Stage[], redo: boolean, index: number) {
        // Only send the description up to the stage that the user submitted
        var desc = $.extend(true, {}, this.experiment.workflowDescription);
        desc.stages = [];
        stages.forEach((stage) => {
            desc.stages.push(stage);
        });
        if (redo) {
            this._resubmitWorkflow(desc, index);
        } else {
            this._submitWorkflow(desc);
        }
    }

    get submitButtonText() {
        if (this._isLastStage(this.currentStage)) {
            return 'Submit';
        } else {
            return 'Next';
        }
    }

    private _submitWorkflow(workflowArgs) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var data = {
            description: workflowArgs
        };
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/submit', data)
        .then((resp) => {
            console.log(resp);
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
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
            console.log(resp)
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
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
            console.log(resp)
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
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
            console.log(resp)
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
            return resp;
            // return $q.reject(resp.data.error);
        });
    }

    private _killWorkflow() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $http.post('/api/experiments/' + this.experiment.id + '/workflow/kill', {})
        .then((resp) => {
            console.log(resp)
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
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
            console.log(resp)
            return resp;
        })
        .catch((resp) => {
            console.log(resp)
            return resp;
            // return $q.reject(resp.data.error);
        });
    }

    private _getWorkflowDescription() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $q.all({
            description: $http.get('/api/experiments/' + this.experiment.id + '/workflow/load')
        }).then((responses: any) => {
           // console.log(responses.taskStatus.data.data)
            this.experiment.workflowDescription = responses.description.data.data;
           return this.experiment.workflowDescription;
        });
    }

    private _getWorkflowStatus() {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        return $q.all({
            status: $http.get('/api/experiments/' + this.experiment.id + '/workflow/status')
        }).then((responses: any) => {
           // console.log(responses.taskStatus.data.data)
            this.experiment.workflowStatus = responses.status.data.data;
           return this.experiment.workflowStatus;
        });
    }

    constructor(public experiment: Experiment,
                public plates: Plate[],
                private _$state,
                private _$interval,
                private _$scope,
                private _$uibModal: ng.ui.bootstrap.IModalService) {
        var uploadStage = {
            name: 'uploadfiles',
            steps: null,
            active: true,
            mode: 'sequential'
        };
        this.currentStage = uploadStage;
        this.stages = [uploadStage].concat(this.experiment.workflowDescription.stages);

        this._$scope.$on('$destroy', () => {
            // stop monitoring when user leaves the "setup" view
            this._stopMonitoring();
        });

        // start monitoring as soon as the user enters the "setup" view
        this._startMonitoring();
    }
}

angular.module('tmaps.ui').controller('SetupCtrl', SetupCtrl);
