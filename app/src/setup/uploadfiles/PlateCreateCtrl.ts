class PlateCreateCtrl {

    error: string;

    static $inject = ['experiment', '$http', '$state'];

    constructor(public experiment: Experiment,
                private _$http,
                private _$state) {}

    createPlate(name: string, description: string) {
        Plate.create(this.experiment.id, {
            name: name,
            description: description
        })
        .then((plate) => {
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
.controller('PlateCreateCtrl', PlateCreateCtrl);
