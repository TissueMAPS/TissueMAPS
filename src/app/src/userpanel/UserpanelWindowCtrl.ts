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

        (new ExperimentDAO()).getAll().then((exps) => {
            this.experiments = <Experiment[]>exps;
        });
    }

    modifyExperiment(e: Experiment) {
        // Enforce re-loading views when switching between experiments
        console.log('modify experiment "' + e.name + '"')
        this._$state.go('plate', {
            stageName: 'upload',
            experimentid: e.id,
            reload: true
        });
    }

    hasChannels(e: Experiment) {
        e.getChannels()
        .then((channels) => {
            if (channels.length == 0) {
                return false;
            }
            return channels.every(function(element, index, array) {
                return element.layers.length > 0;
            });
        })
    }

    viewExperiment(e: Experiment) {
        console.log('view experiment "' + e.name + '"')
        // TODO: modal with error when experiment doesn't have any channels yet
        this._$state.go('viewer', {
            experimentid: e.id
        });
    }

    deleteExperiment(e: Experiment) {
        this._dialogService.warning('Are you sure you want to delete this experiment?')
        .then((answer) => {
            return (new ExperimentDAO()).delete(e.id)
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
