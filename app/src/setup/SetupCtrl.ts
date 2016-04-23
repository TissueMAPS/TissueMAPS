class SetupCtrl {

    currentStage;
    stages;

    static $inject = ['experiment', 'workflowDescription', 'plates', '$state'];

    isInStage(stage) {
        return this.currentStage.name === stage.name;
    }

    goToStage(stage) {
        this.currentStage = stage;
        if (stage.name === 'uploadfiles') {
            this._$state.go('plate');
        } else {
            this._$state.go('setup.stage', {
                stageName: stage.name
            });
        }
    }

    private _checkArgsForWorkflowStage(stage): boolean {
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

        var areStagesOk: boolean[] =  stage.steps.map((step) => {
            batchArgsAreValid = checkArgs(step.batch_args);
            submissionArgsAreValid = checkArgs(step.submission_args);

            if (step.extra_args) {
                extraArgsAreValid = checkArgs(step.extra_args);
            } else {
                extraArgsAreValid = true;
            }

            return batchArgsAreValid && submissionArgsAreValid && extraArgsAreValid;
        });
        return _.all(areStagesOk);
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
        var areWorkflowStagesOk = _.all(this.workflowDescription.stages.map((st) => {
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
            return this._areAllStagesOk();
        } else {
            if (this.currentStage.name !== 'uploadfiles') {
                return this._checkArgsForWorkflowStage(this.currentStage);
            } else {
                return this._isUploadStageOk();
            }
        }
    }

    goToNextStage() {
        var idx = this.stages.indexOf(this.currentStage);
        if (idx >= 0) {
            var inLastStage = idx == this.stages.length - 1
            if (inLastStage) {
                if (this._areAllStagesOk()) {
                    console.log('SUBMIT');
                    this._submitWorkflow();
                } else {
                    console.log('SOME STAGES NOT OK, CANNOT SUBMIT');
                }
            } else {
                var newStage = this.stages[idx + 1];
                this.currentStage = newStage;
                this._$state.go('setup.stage', {
                    stageName: newStage.name
                }, {
                    reload: 'setup.stage'
                });
            }
        }
    }

    private _submitWorkflow() {
        var desc = $.extend(true, {}, this.workflowDescription);
        desc.stages.forEach((stage) => {
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
        });
        this.experiment.submitWorkflow(desc);
    }

    get submitButtonText() {
        if (this._isLastStage(this.currentStage)) {
            return 'Submit';
        } else {
            return 'Next';
        }
    }

    constructor(public experiment: Experiment,
                public workflowDescription: any,
                public plates: Plate[],
                private _$state) {
        var uploadStage = {
            name: 'uploadfiles'
        };
        this.currentStage = uploadStage;
        this.stages = [uploadStage].concat(workflowDescription.stages);
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

    // switch(experiment.status) {
    //     $state.go('uploadfiles');
    //     case 'WAITING_FOR_UPLOAD':
    //     case 'UPLOADING':
    //     case 'DONE':
    //         break;
    //     case 'WAITING_FOR_IMAGE_CONVERSION':
    //     case 'CONVERTING_IMAGES':
    //         $state.go('imageconversion');
    //         break;
    //     case 'WAITING_FOR_PYRAMID_CREATION':
    //     case 'CREATING_PYRAMIDS':
    //         $state.go('pyramidcreation');
    //         break;
    //         $state.go('uploadfiles');
    //     default:
    //         throw new Error(
    //             'Unknown stage: ' + experiment.creationStage
    //         );
    // }
}

angular.module('tmaps.ui').controller('SetupCtrl', SetupCtrl);
