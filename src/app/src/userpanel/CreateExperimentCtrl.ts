class CreateExperimentCtrl {

    error: string;
    supportedMicroscopeTypes: any;
    supportedAcquisitionModes: any;

    opt = {
        name: undefined,
        description: '',
        plateFormat: '384',
        microscopeType: 'cellvoyager',
        plateAcquisitionMode: 'basic'
    };

    private _$http: ng.IHttpService;
    private _$q: ng.IQService;
    static $inject = ['$scope', '$state'];

    constructor(private _$scope, private _$state) {
        this._$http = $injector.get<ng.IHttpService>('$http');
        this._$q = $injector.get<ng.IQService>('$q');
        this._getMicroscopeTypes();
        this._getAcquisitionModes();
    }

    private _getMicroscopeTypes(): ng.IPromise<any> {
        return this._$http.get('/api/microscope_types')
        .then((resp: any) => {
            // console.log(resp)
            // experiment.workflowDescription = resp.data.data;
            this.supportedMicroscopeTypes = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    private _getAcquisitionModes(): ng.IPromise<any> {
        return this._$http.get('/api/acquisition_modes')
        .then((resp: any) => {
            // console.log(resp)
            // experiment.workflowDescription = resp.data.data;
            this.supportedAcquisitionModes = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

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
