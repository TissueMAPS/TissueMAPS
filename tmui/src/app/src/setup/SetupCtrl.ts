// Copyright (C) 2016-2018 University of Zurich.
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
        // var result = {
        //     success: false,
        //     message: 'Not yet implemented'
        // };
        var result = this._workflowService.kill(this.experiment)
        .then(function(res) {
            return {
                success: res.status == 200,
                message: res.statusText
            }
        });
        this._displayResult('Kill', result);
    }

    editPipeline() {
        // TODO: create pipeline if none exists yet
        this._$state.go('project', {experimentid: this.experiment.id});
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
        this._workflowService.getLogOutput(this.experiment, job.id)
        .then((res) => {
            var result = {
                success: res.status == 200,
                message: res.statusText
            };
            if (result.success) {
                var log = res.data.data;
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

    private _createJteratorProject(templateName) {
        var $http = $injector.get<ng.IHttpService>('$http');
        var $q = $injector.get<ng.IQService>('$q');
        var url = '/jtui/experiments/' + this.experiment.id + '/project';
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
