class PlateDetailCtrl {

    error: string;

    static $inject = ['plate', '$state'];

    constructor(public plate: Plate, private _$state) {}

    createAcquisition(name: string, description: string) {
        Acquisition.create(this.plate.id, {
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
        Acquisition.delete(acq.id)
        .then((resp) => {
            this._$state.go('plate.detail', {}, {
                reload: 'plate.detail'
            });
        })
        .catch((error) => {
            this.error = error.message;
        });
    }
}

angular.module('tmaps.ui')
.controller('PlateDetailCtrl', PlateDetailCtrl);


