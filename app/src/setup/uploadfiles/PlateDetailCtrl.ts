class PlateDetailCtrl {

    error: string;

    static $inject = ['plate', '$state', 'dialogService'];

    constructor(public plate: Plate,
                private _$state,
                private _dialogService: DialogService) {}

    createAcquisition(name: string, description: string) {
        (new AcquisitionDAO()).create({
            plate_id: this.plate.id,
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
                (new AcquisitionDAO()).delete(acq.id)
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


