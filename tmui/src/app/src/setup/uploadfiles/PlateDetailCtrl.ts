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
class PlateDetailCtrl {

    error: string;

    static $inject = ['plate', 'dialogService', '$state', '$stateParams'];

    constructor(public plate: Plate,
                private _dialogService: DialogService,
                private _$state,
                private _$stateParams) {}

    createAcquisition(name: string, description: string) {
        (new AcquisitionDAO(this._$stateParams.experimentid)).create({
            plate_name: this.plate.name,
            name: name,
            description: description
        })
        .then((acq) => {
            this._$state.go('plate', {}, {
                reload: 'plate'
            });
        })
        .catch((error) => {
            this.error = error.message;
        });
    }

    deleteAcquisition(acq: Acquisition) {
        this._dialogService.warning('Are you sure you want to delete this acquisition?')
        .then((deleteForReal) => {
            if (deleteForReal) {
                // console.log('delete acquisition HAAAARD')
                (new AcquisitionDAO(this._$stateParams.experimentid)).delete(acq.id)
                .then((resp) => {
                    this._$state.go('plate.detail', {}, {
                        reload: 'plate.detail'
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
.controller('PlateDetailCtrl', PlateDetailCtrl);


class AcquisitionTabCtrl {

    nFiles: number;

    static $inject = ['$scope'];

    constructor(private _$scope) {
        this._$scope.aq.getUploadedFileCount()
        .then((count) => {
            this._$scope.nFiles = count;
        })
    }
}

angular.module('tmaps.ui')
.controller('AcquisitionTabCtrl', AcquisitionTabCtrl);
