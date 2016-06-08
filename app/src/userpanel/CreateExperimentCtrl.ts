class CreateExperimentCtrl {

    error: string;

    opt = {
        name: undefined,
        description: '',
        plateFormat: '384',
        microscopeType: 'cellvoyager',
        plateAcquisitionMode: 'basic'
    };

    static $inject = ['$scope', '$state'];

    constructor(private _$scope, private _$state) {}

    createExperiment() {
        var opt = this.opt;
        return (new ExperimentDAO()).create({
            name: opt.name,
            description: opt.description,
            plate_format: parseInt(opt.plateFormat),
            microscope_type: opt.microscopeType,
            plate_acquisition_mode: opt.plateAcquisitionMode
        }).then((exp) => {
            this._$state.go('userpanel.experiment.list', {}, {
                reload: 'userpanel'
            });
        }).catch((err) => {
            this.error = err;
        });
    }

    get canCreateExperiment() {
        return this.opt.name !== undefined &&
               this.opt.plateFormat !== undefined &&
               this.opt.microscopeType !== undefined &&
               this.opt.plateAcquisitionMode !== undefined;
    }

}

angular.module('tmaps.ui').controller('CreateExperimentCtrl', CreateExperimentCtrl);
