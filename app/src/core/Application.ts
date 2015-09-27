class Application {

    appInstances: AppInstance[] = [];

    private viewportContainerId = 'viewports';
    private activeAppInstanceNumber = 0;

    static $inject = [
        '$q',
        '$',
        'openlayers',
        'experimentFactory',
        'appInstanceFactory',
        'appInstanceDeserializer'
    ];

    constructor(private $q: ng.IQService,
                private $: JQueryStatic,
                private ol,
                private experimentFty: ExperimentFactory,
                private appInstanceFty: AppInstanceFactory,
                private appInstanceDeserializer: AppInstanceDeserializer) {

        // Check if the executing browser is PhantomJS (= code runs in
        // testing mode.
        var isPhantom = /PhantomJS/.test(window.navigator.userAgent);
        if (!isPhantom && !ol.has.WEBGL) {
            throw new Error('TissueMAPS requires a browser supporting WebGL!');
        }
    }

    /**
     * Hide the whole viewport part of TissueMAPS.
     * Note that this will keep the active viewports. After calling
     * `showViewports` the state will be restored.
     * This function is called whenever the route sate changes away from the
     * visualization state.
     */
    hideViewports() {
        this.$('.app').hide();
    }

    /**
     * Show the appInstances after hiding them with `hideViewports`.
     */
    showViewports() {
        this.$('.app').show();
        this.appInstances.forEach((inst) => {
            inst.viewport.map.then(function(map) {
                map.updateSize();
            });
        });
    }

    removeAppInstance(num: number) {
        this.appInstances[num].destroy();
        this.appInstances.splice(num, 1);
        if (num === this.activeAppInstanceNumber) {
            if (num >= 1) {
                // There are still insts with lower number
                this.setActiveAppInstanceByNumber(num - 1);
            } else if (this.appInstances.length > 0) {
                // There are still inst(s) with higher number
                this.setActiveAppInstanceByNumber(0);
            } else {
                // this was the last inst
            }
        }
    }

    destroyAllAppInstances() {
        for (var i in this.appInstances) {
            this.appInstances[i].destroy();
            this.appInstances.splice(i, 1);
        }
        this.activeAppInstanceNumber = -1;
    }

    setActiveAppInstanceByNumber(num: number) {
        var oldActive = this.getActiveAppInstance();
        this.activeAppInstanceNumber = num;
        var newActive = this.getActiveAppInstance();
        if (oldActive) {
            // If the inst wasn't deleted
            oldActive.setInactive();
        }
        newActive.setActive();
    }

    setActiveAppInstance(inst: AppInstance) {
        var nr = this.appInstances.indexOf(inst);
        this.setActiveAppInstanceByNumber(nr);
    }

    getActiveAppInstanceNumber(): number {
        return this.activeAppInstanceNumber;
    }

    // TODO: Remove as many dependencies on this function as possible!
    // Widgets etc. should know the appInstance they belong to.
    getActiveAppInstance(): AppInstance {
        return this.appInstances[this.activeAppInstanceNumber];
    }

    addExperiment(experiment: ExperimentAPIObject) {
        // TODO: Depending on the experiment's type, create a different type of appInstance.
        // TODO: Class viewport and experiment should be abstract.
        var exp = this.experimentFty.createFromServerResponse(experiment);
        var inst = this.appInstanceFty.create(exp);
        inst.addExperimentToViewport();

        this.appInstances.push(inst);
        if (this.appInstances.length === 1) {
            this.setActiveAppInstance(inst);
        }

        return inst;
    }

    serialize(): ng.IPromise<SerializedApplication> {
        var instPromises = _(this.appInstances).map((inst) => {
            return inst.serialize();
        });
        return this.$q.all(instPromises).then((sers) => {
            var serApp =  {
                activeAppInstanceNumber: this.activeAppInstanceNumber,
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
