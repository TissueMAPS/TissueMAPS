class UserpanelWindowCtrl {

    experiments: Experiment[] = [];

    experimentQuery = {
        name: ''
    };

    user: any;

    static $inject = ['application', 'session', '$state', 'dialogService'];

    constructor(private _viewerApp: Application,
                private _session: any,
                private _$state: any,
                private _dialogService: DialogService) {
        this.user = _session.getUser();

        Experiment.getAll().then((exps) => {
            this.experiments = exps;
        });
    }

    modifyExperiment(e: Experiment) {
        this._$state.go('setup', {
            experimentid: e.id
        });
    }

    viewExperiment(e: Experiment) {
        // this._viewerApp.viewExperiment(e);
        this._$state.go('viewer', {
            experimentid: e.id
        });
    };

    deleteExperiment(e: Experiment) {
        this._dialogService.warning('Are you sure you want to delete this experiment?')
        .then((answer) => {
            return Experiment.delete(e.id)
            .then((ok) => {
                if (ok) {
                    var idx = this.experiments.indexOf(e);
                    this.experiments.splice(idx, 1);
                    return true;
                } else {
                    return false;
                }
            })
            .catch((resp) => {
                console.log(resp);
            });
        });
    }
    
}

angular.module('tmaps.ui').controller('UserpanelWindowCtrl', UserpanelWindowCtrl);
