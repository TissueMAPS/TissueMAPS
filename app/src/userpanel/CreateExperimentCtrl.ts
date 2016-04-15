class CreateExperimentCtrl {

    error: string;

    opt = {
        name: undefined,
        description: '',
        plateFormat: '1',
        microscopeType: 'visiview',
        plateAcquisitionMode: 'multiplexing'
    };

    static $inject = ['$scope', '$state'];

    constructor(private _$scope, private _$state) {}

    createExperiment() {
        var opt = this.opt;
        return Experiment.create({
            name: opt.name,
            description: opt.description,
            plateFormat: parseInt(opt.plateFormat),
            microscopeType: opt.microscopeType,
            plateAcquisitionMode: opt.plateAcquisitionMode
        }).then((exp) => {
            this._$state.go('experiment.list', {}, {
                reload: 'experiment.list'
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
