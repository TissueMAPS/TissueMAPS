class WorkflowService {
    workflow: Workflow;
    plates: any;  // TypeScript doesn't like Plate[] here ???

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;

    static $inject = ['$state'];

    constructor(private _$state) {
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

    getPlates(experiment: Experiment): ng.IPromise<any> {
        return (new PlateDAO()).getAll({
            experiment_id: experiment.id
        }).then((plates) => {
            // console.log(plates)
            this.plates = plates;
            return plates;
        })
        .catch((error) => {
            return this._$q.reject(error);
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
            this.workflow.status = new JobCollectionStatus(workflowStatus);
            this.workflow.stages.map((stage, stageIndex) => {
                if (stageIndex == 0 && stage.name == 'upload') {
                    // hack around "upload" stage
                    this.getPlates(experiment)
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
                                workflowStatus.subtasks[stageIndex - 1]
                            );
                            step.jobs = [];
                            workflowStatus.subtasks[stageIndex - 1].subtasks.map((phase, index) => {
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

    getWorkflow(experiment: Experiment): ng.IPromise<any> {
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

