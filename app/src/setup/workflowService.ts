class WorkflowService {
    workflow: Workflow;

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    constructor() {
        // TODO: inject experiment and plates
        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
    }

    private _getWorkflowDescription(experiment: Experiment): ng.IPromise<any> {
        return this._$http.get('/api/experiments/' + experiment.id + '/workflow/load')
        .then((resp: any) => {
            // console.log(resp)
            experiment.workflowDescription = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    private _getUploadStatus(plates: Plate[]) {
        // TODO: this could be done server side based on the database entries
        // and included in the workflow status
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
            this.workflow.status = new JobCollectionStatus(workflowStatus);
            this.workflow.stages.map((stage, stageIndex) => {
                if (stageIndex == 0 && stage.name == 'upload') {
                    // hack around "upload" stage
                    stage.status = this._getUploadStatus(plates);
                } else {
                    var workflowStageDescription = description.stages[stageIndex - 1];
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
                            var workflowStepDescription = workflowStageDescription.steps[stepIndex];
                            var workflowStepStatus = workflowStageStatus.subtasks[stepIndex];
                            step.status = new JobCollectionStatus(workflowStepStatus);
                            // TODO:
                            step.jobs = [];
                            workflowStepStatus.subtasks.map((phase, index) => {
                                if (phase.subtasks.length > 0) {
                                    phase.subtasks.map((subphase, index) => {
                                        if (subphase.subtasks.length > 0) {
                                            subphase.subtasks.map((job) => {
                                                step.jobs.push(new Job(job));
                                            });
                                        } else {
                                            step.jobs.push(new Job(subphase));
                                        }
                                    });
                                } else {
                                    step.jobs.push(new Job(phase));
                                }
                            });
                        }
                    });
                }
            });
        });
        return this.workflow;
    }

    get(experiment: Experiment): ng.IPromise<any> {
        var def = this._$q.defer();
        if (this.workflow) {
            def.resolve(this.workflow);
            return def.promise;
        }
        else {
            this._getWorkflowDescription(experiment);
            return this._getWorkflowStatus(experiment)
            .then((workflowStatus) => {
                // console.log(workflowStatus)
                // TODO: handle null status
                this.workflow = new Workflow(
                    experiment.workflowDescription, workflowStatus
                );
                return this.workflow;
            });
        }
    }

    save(experiment: Experiment) {
        return this._saveWorkflowDescription(experiment);
    }

    private _saveWorkflowDescription(experiment: Experiment) {
        var index = this.workflow.stages.length - 1;
        var data = {
            description: this.workflow.getDescription(index)
        };
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/save', data)
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
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/submit', data)
        .then((resp) => {
            // console.log(resp);
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

    getLogOutput(experiment: Experiment, jobId: number) {
        var data = {
            id: jobId
        };
        return this._$http.post('/api/experiments/' + experiment.id + '/workflow/log', data)
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

