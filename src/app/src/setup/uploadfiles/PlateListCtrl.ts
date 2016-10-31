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
class PlateListCtrl {

    error: string;

    static $inject = ['plates', 'experiment', 'dialogService', '$http', '$state'];

    constructor(public plates: Plate[],
                public experiment: Experiment,
                private _dialogService: DialogService,
                private _$http: ng.IHttpService,
                private _$state: any) {}

    deletePlate(plate: Plate) {
        this._dialogService.warning('Are you sure you want to delete this plate?')
        .then((deleteForReal) => {
            if (deleteForReal) {
                // console.log('delete plate HAAAARD')
                (new PlateDAO(this.experiment.id)).delete(plate.id)
                .then((resp) => {
                    this._$state.go('plate', {}, {
                        reload: 'setup'
                    });
                })
                .catch((error) => {
                    this.error = error.message;
                });
            }
        });
    }

}

angular.module('tmaps.ui')
.controller('PlateListCtrl', PlateListCtrl);


