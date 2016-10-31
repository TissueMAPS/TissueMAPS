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
