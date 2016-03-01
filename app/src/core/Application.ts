// TODO: Rename to ViewerApp
class Application {

    appInstances: AppInstance[] = [];

    private _activeAppInstanceNumber = 0;

    static $inject = [
        '$q',
        '$',
        'openlayers'
    ];

    constructor(private $q: ng.IQService,
                private $: JQueryStatic,
                private ol) {
        // Check if the executing browser is PhantomJS (= code runs in
        // testing mode.
        var isPhantom = /PhantomJS/.test(window.navigator.userAgent);
        if (!isPhantom && !ol.has.WEBGL) {
            throw new Error('TissueMAPS requires a browser supporting WebGL!');
        }
    }

    removeViewer(viewer: AppInstance) {
        var idx = this.appInstances.indexOf(viewer);
        if (idx > -1) {
            var viewer = this.appInstances[idx];
            viewer.destroy();
            this.appInstances.splice(idx, 1);
        }
    }

    /**
     * Hide the whole viewport part of TissueMAPS.
     * Note that this will keep the active viewports. After calling
     * `showViewports` the state will be restored.
     * This function is called whenever the route sate changes away from the
     * visualization state.
     */
    hide() {
        this.$('#viewer-window').hide();
    }

    /**
     * Show the appInstances after hiding them with `hideViewports`.
     */
    show() {
        this.$('#viewer-window').show();
        this.appInstances.forEach((inst) => {
            inst.viewport.update();
        });
    }

    viewExperiment(experiment: Experiment) {
        // TODO: Depending on the experiment's type, create a different type of appInstance.
        // TODO: Class viewport and experiment should be abstract.
        var isFirstExperiment = this.appInstances.length === 0;
        var inst = new AppInstance(experiment, {
            active: isFirstExperiment
        });
        this.appInstances.push(inst);

        return inst;
    }

    serialize(): ng.IPromise<SerializedApplication> {
        var instPromises = _(this.appInstances).map((inst) => {
            return inst.serialize();
        });
        return this.$q.all(instPromises).then((sers) => {
            var serApp =  {
                activeAppInstanceNumber: this._activeAppInstanceNumber,
                appInstances: sers
            };
            return serApp;
        });
    }
}

angular.module('tmaps.core').service('application', Application);

interface SerializedApplication extends Serialized<Application> {
    activeAppInstanceNumber: number;
    appInstances: SerializedAppInstance[];
}
