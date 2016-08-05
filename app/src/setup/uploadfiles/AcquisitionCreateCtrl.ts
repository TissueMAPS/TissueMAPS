class AcquisitionCreateCtrl {

    error: string;

    static $inject = ['plate', '$http', '$state'];

    constructor(public plate: Plate, private _$http, private _$state) {}

    createAcquisition(name: string, description: string) {
        (new AcquisitionDAO(this.plate.experimentId)).create({
            plate_name: this.plate.name,
            name: name,
            description: description
        })
        .then((acq) => {
            this._$state.go('plate.detail', {
                plateid: this.plate.id
            }, {
                reload: 'plate.detail'
            });
        })
        .catch((error) => {
            this.error = error.message;
        });
    }

}

angular.module('tmaps.ui')
.controller('AcquisitionCreateCtrl', AcquisitionCreateCtrl);
