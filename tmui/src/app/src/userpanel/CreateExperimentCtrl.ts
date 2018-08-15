// Copyright 2016 Markus D. Herrmann, University of Zurich and Robin Hafen
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
class CreateExperimentCtrl {

    error: string;
    supportedWorkflowTypes: any;
    supportedMicroscopeTypes: any;
    supportedAcquisitionModes: any;

    opt = {
        name: undefined,
        description: '',
        workflowType: 'canonical',
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
        this._getWorkflowTypes();
        this._getMicroscopeTypes();
        this._getAcquisitionModes();
    }

    private _getMicroscopeTypes(): ng.IPromise<any> {
        return this._$http.get('/api/microscope_types')
        .then((resp: any) => {
            // console.log(resp)
            this.supportedMicroscopeTypes = resp.data.data;
            return resp.data.data;
        })
        .catch((resp) => {
            return this._$q.reject(resp.data.error);
        });
    }

    private _getWorkflowTypes(): ng.IPromise<any> {
        return this._$http.get('/api/workflow_types')
        .then((resp: any) => {
            // console.log(resp)
            this.supportedWorkflowTypes = resp.data.data;
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
            workflow_type: opt.workflowType,
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
