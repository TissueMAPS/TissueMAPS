class UserpanelWindowCtrl {

    experiments: Experiment[] = [];

    experimentQuery = {
        name: ''
    };

    user: any;

    static $inject = ['application', 'session', '$state'];

    viewExperiment(e: Experiment) {
        // this._viewerApp.viewExperiment(e);
        this._$state.go('viewer', {
            experimentid: e.id
        });
    };
    
    constructor(private _viewerApp: Application,
                private _session: any,
                private _$state: any) {
        this.user = _session.getUser();

        Experiment.getAll().then((exps) => {
            this.experiments = exps;
        });
    }
}

angular.module('tmaps.ui').controller('UserpanelWindowCtrl', UserpanelWindowCtrl);
