class SetupCtrl {

    currentStage;

    static $inject = ['experiment', 'workflowDescription', '$state'];

    get inUploadFiles() {
        return this.currentStage.name === 'uploadfiles';
    }

    isInStage(stage) {
        return this.currentStage.name === stage.name;
    }

    goToUploadFiles() {
        this.currentStage = {
            name: 'uploadfiles'
        };
        this._$state.go('plate');
    }

    goToStage(stage) {
        this.currentStage = stage;
        this._$state.go('setup.stage', {
            stageName: stage.name
        });
    }

    private _checkArgsForStage(stage): boolean {
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

    private _areAllStagesOk(): boolean {
        return _.all(this.workflowDescription.stages.map((st) => {
            return this._checkArgsForStage(st);
        }))
    }

    private _isLastStage(stage): boolean {
        var stages = this.workflowDescription.stages;
        var idx = stages.indexOf(stage);
        return idx === stages.length - 1;
    }

    canProceedToNextStage(): boolean {
        if (this._isLastStage(this.currentStage)) {
            return this._areAllStagesOk();
        } else {
            return this._checkArgsForStage(this.currentStage);
        }
    }

    goToNextStage() {
        var stages = this.workflowDescription.stages;
        if (this.currentStage.name == 'uploadfiles') {
            this._$state.go('setup.stage', {
                stageName: this.workflowDescription.stages[0].name
            });
        } else {
            var idx = stages.indexOf(this.currentStage);
            if (idx >= 0) {
                var inLastStage = idx == stages.length - 1
                if (inLastStage) {
                    if (this._areAllStagesOk()) {
                        console.log('SUBMIT');
                        this._submitWorkflow();
                    } else {
                        console.log('SOME STAGES NOT OK, CANNOT SUBMIT');
                    }
                } else {
                    var newStage = stages[idx + 1];
                    this.currentStage = newStage;
                    this._$state.go('setup.stage', {
                        stageName: newStage.name
                    }, {
                        reload: 'setup.stage'
                    });
                }
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
        if (this.currentStage.name === 'image_analysis') {
            return 'Submit';
        } else {
            return 'Next';
        }
    }

    constructor(public experiment: Experiment,
                public workflowDescription: any,
                private _$state) {
        // TODO: remove
        console.log(workflowDescription);
        this.currentStage = workflowDescription.stages[0];
        window['wfd'] = this.workflowDescription;
        switch(experiment.status) {
            case 'WAITING':
                console.log('REDIRECT');
                // this._$state.go('plate');
                // this.currentStage = 'uploadfiles';
                break;
            default:
                throw new Error(
                    'Unknown experiment status: ' + experiment.status
                );
        }
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
