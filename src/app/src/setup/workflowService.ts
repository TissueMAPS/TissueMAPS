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
class WorkflowService {
    workflow: Workflow;

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    static $inject = ['$state', '$rootScope'];

    constructor(private _$state, private _$rootScope) {
        // TODO: inject experiment and plates
        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
    }

    private _getWorkflowDescription(experiment: Experiment): ng.IPromise<any> {
        return this._$http.get('/api/experiments/' + experiment.id + '/workflow/description')
        .then((resp: any) => {
            // console.log(resp)
            // experiment.workflowDescription = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    private _getUploadStatus(plates: Plate[]) {
        var uploadStatus;
        // console.log(this._$state.params)
        var inAcquisitionView = 'acquisitionid' in this._$state.params;
        // console.log(plates)
        var noPlates = plates.length == 0;
        var noAcquisitions = plates.every((p) => {
            return p.acquisitions.length == 0;
        });
        if (noPlates || noAcquisitions) {
            uploadStatus = new JobCollectionStatus({
                failed: false,
                state: '',
                done: false,
                created_at: '',
                updated_at: '',
                percent_done: 0,
                subtasks: [],
                name: 'upload',
                live: false,
                memory: null,
                type: null,
                exitcode: null,
                id: null,
                submission_id: null,
                time: null,
                cpu_time: null
            });
        } else {
            var uploadFailed = false;
            var processingState = '';
            var uploadStates = [];
            var uploadProgress = 0;
            var doneCount = 0;
            var totalCount = 0;
            plates.map((plt) => {
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
            if (plates.every((p) => {return p.status == 'COMPLETE';})) {
                processingState = 'TERMINATED';
            } else if (plates.every((p) => {return p.status == 'WAITING';})) {
                processingState = 'NEW';
            } else if (!inAcquisitionView) {
                // The upload must have been stopped when the user left
                // the acquisition view.
                processingState = 'STOPPED';
            } else {
                // TODO
                processingState = 'RUNNING';
            }
            uploadStatus = new JobCollectionStatus({
                failed: uploadFailed,
                state: processingState,
                created_at: '',
                updated_at: '',
                percent_done: uploadProgress,
                done: uploadProgress == 100,
                subtasks: [],
                name: 'upload',
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
        return uploadStatus;
    }

    private _getWorkflowStatus(experiment: Experiment): ng.IPromise<any> {
        return this._$http.get('/api/experiments/' + experiment.id + '/workflow/status')
        .then((resp: any) => {
            // console.log(resp)
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    update(experiment: Experiment, plates: Plate[]): Workflow {
        console.log('update workflow')
        var index = this.workflow.stages.length - 1;
        this._getWorkflowStatus(experiment)
        .then((workflowStatus) => {
            // recursively update the tree
            // console.log(workflowStatus)
            var description = this.workflow.getDescription(index);
            // TODO: This should not be stored on an attribute of the service
            // class.
            this.workflow.status = new JobCollectionStatus(workflowStatus);
            this.workflow.stages.map((stage, stageIndex) => {
                if (stageIndex == 0 && stage.name == 'upload') {
                    // hack around "upload" stage
                    experiment.getPlates()
                    .then((plates) => {
                        stage.status = this._getUploadStatus(plates);
                    })
                } else {
                    if (workflowStatus == null) {
                        return this.workflow;
                    }
                    var workflowStageDescription = description.stages[stageIndex - 1];
                    if (stageIndex - 1 < workflowStatus.subtasks.length) {
                        stage.status = new JobCollectionStatus(
                            workflowStatus.subtasks[stageIndex - 1]
                        );
                    }
                    // NOTE: The list of jobs within a step is subject to change,
                    // since steps are build dynamically upon processing.
                    // Therefore, we recreate the whole step, rather than just
                    // updating its status.
                    stage.steps.map((step, stepIndex) => {
                        if (workflowStatus.subtasks[stageIndex - 1] != null) {
                            var workflowStepDescription = workflowStageDescription.steps[stepIndex];
                            step.status = new JobCollectionStatus(
                                workflowStatus.subtasks[stageIndex - 1].subtasks[stepIndex]
                            );
                            // TODO: don't just reload the whole datasource,
                            // but only some jobs selectively
                            this._$rootScope.$emit('updateJobStatus', step.name);
                        }
                    });
                }
            });
        });
        return this.workflow;
    }

    getWorkflow(experiment: Experiment): ng.IPromise<any> {
        var def = this._$q.defer();
        if (this.workflow) {
            def.resolve(this.workflow);
            return def.promise;
        }
        else {
            return this._getWorkflowDescription(experiment)
            .then((workflowDescription) => {
                return this._getWorkflowStatus(experiment)
                .then((workflowStatus) => {
                    // console.log(workflowDescription)
                    // console.log(workflowStatus)
                    // TODO: handle null status
                    this.workflow = new Workflow(
                        workflowDescription, workflowStatus
                    );
                    return this.workflow;
                });
            })
        }
    }

    save(experiment: Experiment) {
        return this._saveWorkflowDescription(experiment);
    }

    private _saveWorkflowDescription(experiment: Experiment) {
        var index = this.workflow.stages.length - 1;
        console.log(this.workflow.getDescription(index))
        var data = {
            description: this.workflow.getDescription(index)
        };
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/description', data)
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

    submit(experiment: Experiment, index: number) {
        var data = {
            description: this.workflow.getDescription(index)
        };
        this._$rootScope.$emit('updateJobStatus')
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/submit', data)
        .then((resp) => {
            // console.log(resp);
            // data.description.stages[index-1].steps.map((step, stepIndex) => {
            //     console.log('UPDATE JOBS for step ', step.name)
            //     return this._$rootScope.$emit('updateJobStatus', step.name);
            // });
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return this._$q.reject(resp.data.error);
        });
    }

    resubmit(experiment: Experiment, index: number, startIndex: number) {
        var data = {
            description: this.workflow.getDescription(index),
            index: startIndex
        };
        this._$rootScope.$emit('updateJobStatus')
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/resubmit', data)
        .then((resp) => {
            // console.log(resp)
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return this._$q.reject(resp.data.error);
        });
    }

    kill(experiment: Experiment) {
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/kill', {})
        .then((resp) => {
            // console.log(resp)
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return this._$q.reject(resp.data.error);
        });
    }

    getLogOutput(experiment: Experiment, jobId: string) {
        console.log(jobId)
        return this._$http.get('/api/experiments/' + experiment.id + '/workflow/jobs/' + jobId + '/log')
        .then((resp) => {
            // console.log(resp)
            return resp;
        })
        .catch((resp) => {
            // console.log(resp)
            return resp;
            // return this._$q.reject(resp.data.error);
        });
    }

}

angular.module('tmaps.ui').service('workflowService', WorkflowService);

