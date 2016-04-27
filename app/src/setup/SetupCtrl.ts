class SetupCtrl {

    currentStage;

    get inUploadFiles() {
        return this.currentStage === 'uploadfiles';
    }

    get inImagePreprocessing() {
        return this.currentStage === 'imageprocessing';
    }

    get inPyramidCreation() {
        return this.currentStage === 'pyramidcreation';
    }

    get inImageAnalysis() {
        return this.currentStage === 'imageanalysis';
    }

    static $inject = ['experiment', '$state'];

    constructor(public experiment: Experiment, private _$state) {
        switch(experiment.status) {
            case 'WAITING':
                this._$state.go('plate');
                this.currentStage = 'uploadfiles';
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
