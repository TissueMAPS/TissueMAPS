class PlateListCtrl {

    error: string;

    static $inject = ['plates', 'experiment', '$http', '$state'];

    constructor(public plates: Plate[],
                public experiment: Experiment,
                private _$http: ng.IHttpService,
                private _$state: any) {}

    deletePlate(plate: Plate) {
        (new PlateDAO()).delete(plate.id)
        .then((resp) => {
            this._$state.go('plate', {}, {
                reload: 'setup'
            });
        })
        .catch((error) => {
            this.error = error.message;
        });
    }
}

angular.module('tmaps.ui')
.controller('PlateListCtrl', PlateListCtrl);


