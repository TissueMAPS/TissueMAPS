interface Stage {
    name: string;
    steps: any[];
}

class SetupCtrl {

    currentStage: Stage;
    currentStageSubmission: any;
    stages: Stage[];
    submission: any;
    _monitoringPromise: ng.IPromise<void> = null;

    static $inject = ['experiment', 'plates', '$state', '$interval', '$scope'];

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

    private _areWorkflowStagesOk() {
        var areWorkflowStagesOk =
            _.all(this.experiment.workflowDescription.stages.map((st) => {
            return this._checkArgsForWorkflowStage(st);
        }));
        return areWorkflowStagesOk;
    }

    private _areAllStagesOk(): boolean {
        return this._isUploadStageOk() && this._areWorkflowStagesOk();
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

    submit() {
        var idx = this.stages.indexOf(this.currentStage);
        var notInUploadFiles = idx > 0;
        if (notInUploadFiles) {
            var isStageOk = this._checkArgsForWorkflowStage(this.currentStage);
            if (isStageOk) {
                var stagesToBeSubmitted = [];
                for (var i = 1; i <= idx;  i++) {
                    stagesToBeSubmitted.push(this.stages[i]);
                }
                // TODO: determine whether upstream stages have been completed
                // and then "resubmit", i.e. resume an existing workflow
                var redo = false;
                this._submitStages(stagesToBeSubmitted, redo, idx);
            }
        }
    }

    canSubmit(): boolean {
        if (this.currentStage.name === 'uploadfiles') {
            // Submit button should not be pressable from upload files stage
            return false;
        } else if (this._isLastStage(this.currentStage)) {
            return this._areAllStagesOk();
        } else {
            return this._checkArgsForWorkflowStage(this.currentStage);
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

    private _updateStageDescription(stage: Stage) {
        // Copy the stage so that we don't modify the argument when
        // modifying the structure of the stage.
        // The structure of the stage objects that were originally sent to the client
        // have a different structure than the ones that are passed back
        // to the server.
        stage = $.extend(true, {}, stage);
        stage.steps.forEach((step) => {
            var batchArgs = {};
            step.batch_args.forEach((arg) => {
                batchArgs[arg.name] = arg.value;
            });
            step.batch_args = batchArgs;

            var submissionArgs = {};
            step.submission_args.forEach((arg) => {
                submissionArgs[arg.name] = arg.value;
            });
            step.submission_args = submissionArgs;

            if (step.extra_args) {
                var extraArgs = {};
                step.extra_args.forEach((arg) => {
                    extraArgs[arg.name] = arg.value;
                });
                step.extra_args = extraArgs;
            } else {
                step.extra_args = null;
            }
        });
        return stage;
    }

    getStatus() {
        console.log('get workflow status')
        this.experiment.getWorkflowStatus();
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
        console.log(this.submission)
        console.log(this.currentStageSubmission)
    }

    // starts the interval
    private _startMonitoring() {
        // stops any running interval to avoid two intervals running at the same time
        this._stopMonitoring();
        this.getStatus();
        console.log('start monitoring status')
        console.log('promise: ', this._monitoringPromise)
        this._monitoringPromise = this._$interval(() => {
                this.getStatus()
            }, 5000
        );
    }

    private _stopMonitoring() {
        console.log('stop monitoring status')
        console.log('promise: ', this._monitoringPromise)
        this._$interval.cancel(this._monitoringPromise);
        console.log('promise: ', this._monitoringPromise)
        this._monitoringPromise = null;
        console.log('promise: ', this._monitoringPromise)
    }

    private _submitStages(stages: Stage[], redo: boolean, index: number) {
        // Copy the original workflow description object and populate it with
        // all the values that were filled in by the user.
        // var desc = this.experiment.workflowDescription;
        var desc = $.extend(true, {}, this.experiment.workflowDescription);
        desc.stages = [];
        stages.forEach((stage) => {
            stage = this._updateStageDescription(stage);
            desc.stages.push(stage);
        });
        if (redo) {
            this.experiment.resubmitWorkflow(desc, index);
        } else {
            this.experiment.submitWorkflow(desc);
        }
    }

    get submitButtonText() {
        if (this._isLastStage(this.currentStage)) {
            return 'Submit';
        } else {
            return 'Next';
        }
    }

    constructor(public experiment: Experiment,
                public plates: Plate[],
                private _$state,
                private _$interval,
                private _$scope) {
        var uploadStage = {
            name: 'uploadfiles',
            steps: null,
        };
        this.currentStage = uploadStage;
        this.stages = [uploadStage].concat(this.experiment.workflowDescription.stages);

        this._$scope.$on('$destroy', () => {
            // stop monitoring when user leaves the "setup" view
            this._stopMonitoring();
        });

        // start monitoring as soon as the user enters the "setup" view
        this._startMonitoring();
        // console.log(experiment);
        // switch(experiment.status) {
        //     case 'WAITING':
        //         this._$state.go('plate');
        //         this.currentStage.name = 'uploadfiles';
        //         break;
        //     default:
        //         throw new Error(
        //             'Unknown experiment status: ' + experiment.status
        //         );
        // }
    }
}

angular.module('tmaps.ui').controller('SetupCtrl', SetupCtrl);
