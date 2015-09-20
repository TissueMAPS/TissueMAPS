class AppstateService {

    private currentState: Appstate;
    lastSavedAt: Date;

    static $inject = [
        'application',
        '$modal',
        '$http',
        '$location',
        'applicationDeserializer',
    ];

    constructor(private application,
                private $modal,
                private $http: ng.IHttpService,
                private $location: ng.ILocationService,
                private applicationDeserializer: ApplicationDeserializer) {
    }

    private setCurrentState = (st: Appstate) => {
        this.currentState = st;
        if (st.isSnapshot) {
            this.$location.search({'snapshot': st.id});
        } else {
            this.$location.search({'state': st.id});
        }
    }

    private toClientRepresentation(st: AppstateAPIObject): Appstate {
        return {
            id: st.id,
            name: st.name,
            owner: st.owner,
            isSnapshot: st.is_snapshot,
            blueprint: st.blueprint
        };
    }

    getCurrentState() {
        return this.currentState;
    }

    hasCurrentState() {
        return this.currentState !== undefined && this.currentState.id !== undefined;
    }

    /**
     * Get all available app states for the current user.
     */
    getStates() {
        return this.$http.get('/api/appstates').then((resp) => {
            var data = <GetAppstatesResponse> resp.data;
            var res = {
                owned: _(data.owned).map(this.toClientRepresentation),
                shared: _(data.shared).map(this.toClientRepresentation)
            };
            return res;
        });
    }

    /**
     * Load an app state into the application.
     */
    loadState(state: Appstate) {
        this.setCurrentState(state);
        this.applicationDeserializer.deserialize(state.blueprint);
    }

    loadStateFromId(id) {
        return this.$http
        .get('/api/appstates/' + id).then((resp) => {
            var data = <AppstateAPIObject> resp.data;
            return data;
        })
        .then(
            (data) => {
                var state = this.toClientRepresentation(data);
                this.loadState(state);
                return state;
            },
            (err) => {
                throw new Error('Server-side error when trying to load state: ' + err);
            }
        );
    }

    /**
     * Ask the server to update the current appstate with a new blueprint.
     * If no app state is active, a 'Save as'-dialog will appear.
     */
    saveState() {
        if (this.currentState.isSnapshot) {
            throw new Error('Can\'t save snapshots!');
        } else if (!this.hasCurrentState()) {
            this.promptForSaveAs();
        } else {
            var id = this.currentState.id;
            this.application.serialize()
            .then((bp) => {
                return this.$http.put('/api/appstates/' + id, {
                    blueprint: bp
                });
            })
            .then((resp) => {
                var state = this.toClientRepresentation(resp.data);
                this.setCurrentState(state);
                this.lastSavedAt = new Date();
            })
            .catch((err) => {
                console.log('There was an error when trying to save app state.', err);
            });
        }
    }

    /**
     * Popup a dialog where the user can enter a name and optional description
     * for the appstate that has to be saved.
     * TODO: Add validation to the dialog.
     */
    promptForSaveAs() {
        var instance = this.$modal.open({
            templateUrl: '/templates/main/appstate/save-appstate-as-dialog.html',
            controller: 'SaveAppstateAsDialogCtrl',
            controllerAs: 'dialog'
        });

        return instance.result.then((res) => {
            return this.saveStateAs(res.name, res.description);
        });
    }

    /**
     * Ask the server to save an appstate under a new name.
     */
    saveStateAs(name: string, description: string) {
        if (this.currentState !== undefined && this.currentState.isSnapshot) {
            throw new Error('A snapshot can\'t be saved under a different name');
        }
        return this.application.serialize()
        .then((bp) => {
            return this.$http.post('/api/appstates', {
                name: name,
                description: description,
                blueprint: bp
            });
        })
        .then((resp) => {
            var state = this.toClientRepresentation(resp.data);
            this.setCurrentState(state);
            this.lastSavedAt = new Date();
        }, (err) => {
            console.log('There was an error when trying to save app state.', err);
        });
    }

    // TODO: Currently only snapshot-sharing is enabled,
    // Split this function into one for normal sharing and one for snapshot sharing
    shareState() {
        if (this.currentState.isSnapshot) {
            throw new Error('A snapshot can\'t be shared again');
        } else if (this.hasCurrentState()) {
            var url = '/api/appstates/' + this.currentState.id + '/snapshots';
            var instance = this.$modal.open({
                templateUrl: '/templates/main/appstate/share-appstate-dialog.html',
                controller: 'ShareAppstateCtrl',
                controllerAs: 'share',
                resolve: {
                    link: ['$http', ($http) => {
                        return this.$http.get(url).then((resp) => {
                            return this.getLinkForSnapshot(resp.data);
                        });
                    }]
                }
            });
        } else {
            throw new Error('Appstate needs to be saved before it can be shared!');
        }
    }

    getLinkForSnapshot(snapshot) {
        var link = 'http://' + this.$location.absUrl();
        if (this.$location.port() !== 80) {
            link += ':' + this.$location.port();
        }
        link += '/#/viewport?snapshot=' + snapshot.id;
        return link;
    }
}

angular.module('tmaps.main.appstate').service('appstateService', AppstateService);
