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


