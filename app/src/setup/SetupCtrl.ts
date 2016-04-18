class SetupCtrl {

    currentStage;
    args: any = {};

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
                    console.log('in last stage');
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

    static $inject = ['experiment', 'workflowDescription', '$state'];

    constructor(public experiment: Experiment,
                public workflowDescription: any,
                private _$state) {
        // TODO: remove
        this.currentStage = workflowDescription.stages[0];
        window['args'] = this.args;
        workflowDescription.stages.forEach((stage) => {
            this.args[stage.name] = {};
            stage.steps.forEach((step) => {
                this.args[stage.name][step.name] = {
                    batch_args: {},
                    submission_args: {}
                };
                step.batch_args.forEach((arg) => {
                    this.args[stage.name][step.name].batch_args[arg.name] = arg.default;
                });
                step.submission_args.forEach((arg) => {
                    this.args[stage.name][step.name].submission_args[arg.name] = arg.default;
                });
            });
        });
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
