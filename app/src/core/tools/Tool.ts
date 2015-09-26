type ToolWindowId = string;

interface ServerToolWindow {
    id: ToolWindowId;
}

class ToolWindow {
    constructor(public id: ToolWindowId,
                public windowHeight: number,
                public windowWidth: number) {}
}

class Tool {
    toolWindows: ToolWindow[];

    constructor(private $: JQueryStatic,
                private $http: ng.IHttpService,
                private $window: Window,
                private $rootScope: ng.IRootScopeService,
                public viewport: Viewport,
                public id: string,
                public name: string,
                public description: string,
                public template: string,
                public icon: string,
                public defaultWindowHeight: number,
                public defaultWindowWidth: number) {
        this.toolWindows = [];
    }

    getIdSlug(): string {
        return this.id.toLowerCase()
                      .replace(/[^A-Za-z0-9]+/g, '-')
                      .replace(/(^-|-$)/g, '');
    }

    createNewWindow(appstate: Appstate, exp: Experiment) {
        this.createToolWindowOnServer(appstate, exp).then((inst) => {
            this.openWindow(inst);
        });
    }

    removeToolWindow(win: ToolWindow) {
        this.deleteToolWindowOnServer(win).then((remoteDeletionOK) => {
            if (remoteDeletionOK) {
                var win = _(this.toolWindows).find((w) => {
                    return w.id === win.id;
                });
                if (win !== undefined) {
                    var idx = this.toolWindows.indexOf(win);
                    this.toolWindows.splice(idx, 1);
                } else {
                    console.log('SHAZBOT, no local window with this id');
                }
            } else {
                console.log('SHAZBOT, could not delete remote window');
            }
        });
    }

    private createToolWindowOnServer(appstate: Appstate, experiment: Experiment): ng.IPromise<ServerToolWindow> {
        return this.$http.post('/tools/' + this.id + '/instances', {
            'appstate_id': appstate.id,
            'experiment_id': experiment.id
        }).then((resp) => {
            console.log('Successfully created a tool instance.');
            return resp.data;
        }, (err) => {
            console.log('Server refused to create a tool instance.', err);
        });
    }

    private deleteToolWindowOnServer(id): ng.IPromise<boolean> {
        return this.$http.delete('/tool_instances/' + id).then((resp) => {
            console.log('Successfully deleted tool instance with id', id);
            return true;
        }, function(err) {
            console.log('There was an error when trying to delete the',
                        'tool instance with ', id, ':', err);
            return false;
        });
    }

    openWindow(instance: ServerToolWindow) {
        // Without appending the current date to the title, the browser (chrome)
        // won't open multiple tool windows of the same type.
        var toolWindow = this.$window.open(
            '/tools/#/' + this.getIdSlug(), this.id, // + Date.now(),
            'toolbar=no,menubar=no,titebar=no,location=no,directories=no,replace=no,' +
            'width=' + this.defaultWindowWidth + ',height=' + this.defaultWindowHeight
        );

        if (_.isUndefined(toolWindow)) {
            throw new Error('Could not create tool window! Is your browser blocking popups?');
        }

        this.$(toolWindow).bind('beforeunload', (event) => {
            this.$http.delete('/tool_instances/' + instance.id)
            .then(function(resp) {
                console.log('Successfully deleted tool instance with id',
                            instance.id);
            }, function(err) {
                console.log('There was an error when trying to delete the',
                            'tool instance with ', instance.id, ':', err);
            });
        });

        // Create a container object that includes ressources that the tool may
        // need.
        var init = {
            tmapsProxy: {
                // The viewport from which this tool was called.
                // The map object is available via this object.
                viewport: this.viewport,
                // TissueMAPS' $rootScope; can be used to listen to
                // events that happen in the main window.
                $rootScope: this.$rootScope
            },
            toolWindow: toolWindow
        };

        // Save the initialization object to the local storage, such that the newly
        // created window may retrieve it.
        toolWindow.init = init;
    }
}
